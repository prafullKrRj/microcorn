import asyncio

from microcorn.loop.loop_factory import get_loop_factory
from microcorn.protocol.factory import get_protocol_factory


async def serve():
    loop = asyncio.get_running_loop()
    server = await loop.create_server(
        protocol_factory=get_protocol_factory(),
        host="0.0.0.0",
        port=8080,
    )
    try:
        await server.serve_forever()
    except Exception:
        print("error")
    finally:
        server.close()


def microcorn_server():
    asyncio.run(serve(), loop_factory=get_loop_factory())


if __name__ == "__main__":
    microcorn_server()


"""
Config -> Server(config) -> Server Runs on loop 
 -> Server State (handling active connections, and tasks) 
 -> For each coming request there is one request response cycle (initiating in the protocol)
 -> request response cycle contains send, receive, scope
 -> protocol -> http parser -> rrc
"""
