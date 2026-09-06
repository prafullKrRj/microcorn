import asyncio
from asyncio import Event, Transport
from typing import Union
from urllib.parse import unquote

import h11
from h11 import NEED_DATA, PAUSED, RemoteProtocolError

from microcorn.protocol.rr_cycle.request_response_cycle import RequestResponseCycle
from microcorn.protocol.rr_cycle.types import ASGIVersions, RequestScope
from microcorn.protocol.transport_flow import TransportFlow

EventType = Union[Event, type[NEED_DATA], type[PAUSED]]


def get_transport_address(transport: Transport, name: str) -> tuple[str, int] | None:
    try:
        info = transport.get_extra_info(name)
        if info is not None and isinstance(info, (list, tuple)) and len(info) == 2:
            return str(info[0]), int(info[1])
        return None
    except OSError:
        print("error")


def get_scope(event: h11.Request) -> RequestScope:
    headers = event.headers
    raw_path, _, query_string = event.target.partition(b"?")

    return RequestScope(
        headers=headers,
        method=event.method.decode("utf-8"),
        http_version=event.http_version.decode("utf-8"),
        query_string=query_string,
        raw_path=raw_path,
        asgi=ASGIVersions(spec_version="2.3", version="2.0"),
        client=None,
        server=None,
        path=unquote(raw_path.decode("ascii")),
        scheme="http",
        root_path="",
        type="http",
    )


class EventHandler:
    def __init__(self, conn: h11.Connection, flow: TransportFlow):
        self.conn: h11.Connection = conn
        self.flow = flow
        self.body = ""
        self.cycle: RequestResponseCycle | None = None

        self.client: tuple[str, int] | None = get_transport_address(
            self.flow.transport, "peername"
        )
        self.server: tuple[str, int] | None = get_transport_address(
            self.flow.transport, "sockname"
        )

    def handle_events(self):
        while True:
            try:
                event: EventType = self.conn.next_event()
            except RemoteProtocolError:
                print("remote protocol error")
                return
            if event is NEED_DATA:
                return
            elif event is PAUSED:
                self.flow.pause_reading()
                break

            elif isinstance(event, h11.Request):
                headers = event.headers
                raw_path, _, query_string = event.target.partition(b"?")
                scope = get_scope(event)
                self.cycle = RequestResponseCycle(
                    conn=self.conn, flow=self.flow, scope=scope, event=asyncio.Event()
                )
                print(scope)
                assert self.cycle
                self.cycle.run_asgi()

            elif isinstance(event, h11.Data):
                assert self.cycle
                if self.conn.our_state is h11.DONE:
                    continue
                self.cycle.body += event.data
                self.cycle.message_event.set()

            elif isinstance(event, h11.EndOfMessage):
                self.cycle.more_body = False
                self.cycle.message_event.set()
                if self.conn.their_state == h11.MUST_CLOSE:
                    break


"""
Sample headers:
<Headers([(b'postman-token', b'2d39be20-48df-422e-ad04-5fb762812ffb'), (b'host', b'localhost:8080'), (b'user-agent', b'PostmanRuntime/2.5.0'), (b'accept', b'*/*'), (b'accept-encoding', b'gzip, deflate, br'), (b'connection', b'keep-alive')])>


With Params:
'/?abc=12'
<Headers([(b'postman-token', b'88027011-b18b-43a3-abeb-a10a686b7824'), (b'content-type', b'application/json'), (b'content-length', b'25'), (b'host', b'localhost:8080'), (b'user-agent', b'PostmanRuntime/2.5.0'), (b'accept', b'*/*'), (b'accept-encoding', b'gzip, deflate, br'), (b'connection', b'keep-alive')])>


Sample Body:
b'POST'
{
    "Name": "Prafull"
}


"""
