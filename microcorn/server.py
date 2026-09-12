import asyncio
from asyncio import AbstractEventLoop, get_running_loop

import uvloop

from microcorn.lifespan import LifeSpan
from microcorn.loop.loop_factory import get_loop_factory
from microcorn.protocol.factory import get_protocol_factory
from microcorn.server_state import ServerState


class MicroCornServer:
    def __init__(self, application, host="127.0.0.1", port=8000):
        self.application = application
        self.host = host
        self.port = port
        self.loop: asyncio.AbstractEventLoop | None = None
        self.server_state = ServerState(tasks=set(), connections=set())
        self.lifespan = LifeSpan(self.application, self.server_state.application_state)

    def set_or_get_running_loop(self) -> AbstractEventLoop:
        if self.loop is None:
            self.loop = get_running_loop()
        return self.loop if self.loop else uvloop.new_event_loop()

    def __create_protocol__(self) -> asyncio.Protocol:
        protocol_class: type[asyncio.Protocol] = get_protocol_factory()
        return protocol_class(
            application=self.application,
            server_state=self.server_state,
            loop=self.set_or_get_running_loop(),
        )

    async def _serve(self, sockets=None):
        self.loop = self.set_or_get_running_loop()
        assert self.loop
        await self.lifespan.startup()
        if self.lifespan.should_exit:
            return
        options = {"protocol_factory": self.__create_protocol__}
        if sockets is None:
            options.update(host=self.host, port=self.port)
        else:
            options["sock"] = sockets
        server = await self.loop.create_server(**options)

        try:
            await server.serve_forever()
        except Exception as err:  # noqa: BLE001 - server boundary logs shutdown errors
            print(f"error: {err}")
        finally:
            server.close()
            await self.lifespan.shutdown()
            await self.server_state.shutdown()
            await self.loop.shutdown_asyncgens()

    def run(self, sockets=None):
        try:
            asyncio.run(self._serve(sockets=sockets), loop_factory=get_loop_factory())
        except Exception as e:  # noqa: BLE001 - sync server boundary
            print(f"error: {e}")


def microcorn_server():
    from microcorn.config import Config

    config = Config("example.main:app")
    server = MicroCornServer(config.load(), config.host, config.port)
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
