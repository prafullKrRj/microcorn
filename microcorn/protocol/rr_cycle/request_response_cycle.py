import asyncio
import http
from abc import ABC

import h11

from microcorn._types import (
    HTTPReceiveEvent,
    HTTPSendEvent,
    RequestScope,
)
from microcorn.protocol.transport_flow import TransportFlow


def _get_status_phrase(status_code: int) -> bytes:
    try:
        return http.HTTPStatus(status_code).phrase.encode()
    except ValueError:
        return b""


STATUS_PHRASES = {
    status_code: _get_status_phrase(status_code) for status_code in range(100, 600)
}


class RRCycle(ABC):
    async def send(self, event: HTTPSendEvent): ...

    async def receive(self): ...

    async def run_asgi(self): ...


class RequestResponseCycle(RRCycle):
    def __init__(
        self,
        scope: RequestScope,
        conn: h11.Connection,
        flow: TransportFlow,
        event: asyncio.Event,
        application=None,
    ):
        self.flow = flow
        self.scope: RequestScope = scope
        self.conn = conn
        self.response_started = False
        self.response_completed = False
        self.message_event: asyncio.Event = event
        self.body: bytes = bytearray()
        self.more_body = True
        self.application = application
        self.scope.setdefault("state", {})

    async def send(self, event: HTTPSendEvent) -> None:
        if not self.response_started:
            if event["type"] != "http.response.start":
                raise RuntimeError("Expected http.response.start")
            self.response_started = True

            status = event["status"]
            headers = list(event["headers"])

            status_reason = STATUS_PHRASES[status]
            h11_response = h11.Response(
                status_code=status,
                headers=headers,
                reason=status_reason,
            )
            output = self.conn.send(event=h11_response)
            self.flow.write(output)
        elif not self.response_completed:
            if event["type"] != "http.response.body":
                raise RuntimeError("Expected http.response.body")

            body = event.get("body", b"")
            more_body = event.get("more_body", False)

            data = b"" if self.scope.get("method") == "HEAD" else body
            output = self.conn.send(h11.Data(data=data))
            self.flow.write(output)

            if not more_body:
                self.response_completed = True
                output = self.conn.send(h11.EndOfMessage())
                self.flow.write(output)
                self.more_body = False

    async def receive(self) -> HTTPReceiveEvent:
        if not self.response_completed:
            self.flow.resume_reading()
            await self.message_event.wait()
            self.message_event.clear()
        response: HTTPReceiveEvent = HTTPReceiveEvent(
            type="http.request",
            body=bytes(self.body),
            more_body=self.more_body,
        )
        print("hello")
        self.body = bytearray()
        return response

    async def run_asgi(self):
        try:
            await self.application(self.scope, self.receive, self.send)
        except Exception:  # noqa: BLE001 - convert app failure to HTTP 500
            if not self.response_started:
                await self.send(
                    {
                        "type": "http.response.start",
                        "status": 500,
                        "headers": [(b"content-type", b"text/plain; charset=utf-8")],
                    }
                )
                await self.send(
                    {"type": "http.response.body", "body": b"Internal Server Error"}
                )
