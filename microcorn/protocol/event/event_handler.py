import asyncio
from asyncio import AbstractEventLoop, Event, Task, Transport
from urllib.parse import unquote

import h11
from h11 import NEED_DATA, PAUSED, RemoteProtocolError

from microcorn._types import ASGIVersions, RequestScope
from microcorn.protocol.rr_cycle.request_response_cycle import RequestResponseCycle
from microcorn.protocol.transport_flow import TransportFlow
from microcorn.server_state import ServerState

EventType = Event | type[NEED_DATA] | type[PAUSED]


def get_transport_address(transport: Transport, name: str) -> tuple[str, int] | None:
    try:
        info = transport.get_extra_info(name)
        if info is not None and isinstance(info, (list, tuple)) and len(info) == 2:
            return str(info[0]), int(info[1])
        return None
    except OSError:
        print("error")


def get_scope(
    event: h11.Request,
    client: tuple[str, int] | None = None,
    server: tuple[str, int] | None = None,
    state: dict | None = None,
) -> RequestScope:
    headers = event.headers
    raw_path, _, query_string = event.target.partition(b"?")

    return RequestScope(
        headers=headers,
        method=event.method.decode("utf-8"),
        http_version=event.http_version.decode("utf-8"),
        query_string=query_string,
        raw_path=raw_path,
        asgi=ASGIVersions(spec_version="2.3", version="2.0"),
        client=client,
        server=server,
        path=unquote(raw_path.decode("ascii")),
        scheme="http",
        root_path="",
        type="http",
        state=state if state is not None else {},
    )


class EventHandler:
    def __init__(
        self,
        conn: h11.Connection,
        flow: TransportFlow,
        tasks: set[Task[None]],
        loop: AbstractEventLoop,
        application=None,
        application_state: dict | None = None,
        server_state: ServerState | None = None,
    ):
        self.conn: h11.Connection = conn
        self.flow = flow
        self.application = application
        self.application_state = (
            application_state if application_state is not None else {}
        )
        self.server_state = server_state
        self.body = ""
        self.cycle: RequestResponseCycle | None = None

        self.client: tuple[str, int] | None = get_transport_address(
            self.flow.transport, "peername"
        )
        self.server: tuple[str, int] | None = get_transport_address(
            self.flow.transport, "sockname"
        )
        self.loop = loop
        self.tasks = tasks

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
                scope = get_scope(
                    event,
                    client=self.client,
                    server=self.server,
                    state=self.application_state,
                )
                self.cycle = RequestResponseCycle(
                    conn=self.conn,
                    flow=self.flow,
                    scope=scope,
                    event=asyncio.Event(),
                    application=self.application,
                )
                assert self.cycle
                task = self.loop.create_task(self.cycle.run_asgi())
                if self.server_state is not None:
                    self.server_state.add_task(task)
                    self.server_state.total_requests += 1
                else:
                    task.add_done_callback(self.tasks.discard)
                    self.tasks.add(task)

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
