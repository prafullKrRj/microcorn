import asyncio
from asyncio import AbstractEventLoop

import h11

from microcorn.protocol.event.event_handler import EventHandler
from microcorn.protocol.transport_flow import TransportFlow
from microcorn.server_state import ServerState


class H11Protocol(asyncio.Protocol):
    def __init__(
        self, server_state: ServerState, loop: AbstractEventLoop | None = None
    ):
        self.transport: asyncio.Transport | None = None
        self.conn = h11.Connection(our_role=h11.SERVER)
        self.event_handler: EventHandler | None = None
        self.__transport_flow: TransportFlow | None = None
        self.loop: AbstractEventLoop | None = loop
        self.server_state: ServerState = server_state
        print(self.loop)

    def __get_transport_flow__(self) -> TransportFlow:
        assert self.transport is not None
        if self.__transport_flow is None:
            self.__transport_flow = TransportFlow(self.transport)
        return self.__transport_flow

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.transport = transport
        self.__get_transport_flow__()

    def connection_lost(self, exc: Exception | None) -> None:
        pass

    def data_received(self, data: bytes) -> None:
        try:
            self.conn.receive_data(data)
            if not self.event_handler:
                self.event_handler = EventHandler(
                    conn=self.conn,
                    flow=self.__get_transport_flow__(),
                    tasks=self.server_state.tasks,
                    loop=self.loop,
                )
            assert self.event_handler is not None
            self.event_handler.handle_events()
        except Exception as ex:
            print(ex)

    def pause_writing(self) -> None:
        self.__get_transport_flow__().pause_writing()

    def resume_writing(self) -> None:
        self.__get_transport_flow__().resume_writing()

    def eof_received(self) -> bool | None:
        pass
