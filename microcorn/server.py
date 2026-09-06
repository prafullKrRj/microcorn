import asyncio
from asyncio import get_running_loop, AbstractEventLoop

import uvloop

from microcorn.loop.loop_factory import get_loop_factory
from microcorn.protocol.factory import get_protocol_factory
from microcorn.server_state import ServerState


class MicroCornServer:
    def __init__(self):
        self.loop: asyncio.AbstractEventLoop | None = None
        self.server_state = ServerState(tasks=set(), connections=set())

    def set_or_get_running_loop(self) -> AbstractEventLoop:
        if self.loop is None:
            self.loop = get_running_loop()
        return self.loop if self.loop else uvloop.new_event_loop()

    def __create_protocol__(self) -> asyncio.Protocol:
        protocol_class: type[asyncio.Protocol] = get_protocol_factory()
        return protocol_class(
            server_state=self.server_state, loop=self.set_or_get_running_loop()
        )

    async def _serve(self):
        self.loop = self.set_or_get_running_loop()
        assert self.loop
        server = await self.loop.create_server(
            protocol_factory=self.__create_protocol__,
            host="0.0.0.0",
            port=8080,
        )

        try:
            await server.serve_forever()
        except Exception as err:
            print(f"error: {err}")
        finally:
            server.close()
            await self.loop.shutdown_asyncgens()

    def run(self):
        try:
            asyncio.run(self._serve(), loop_factory=get_loop_factory())
        except Exception as e:
            print(f"error: {e}")


def microcorn_server():
    server = MicroCornServer()
    server.run()


if __name__ == "__main__":
    microcorn_server()


"""
Config -> Server(config) -> Server Runs on loop 
 -> Server State (handling active connections, and tasks) 
 -> For each coming request there is one request response cycle (initiating in the protocol)
 -> request response cycle contains send, receive, scope
 -> protocol -> http parser -> rrc
"""
