import uvloop
import asyncio


callable: asyncio.AbstractEventLoop = uvloop.new_event_loop()
c2: asyncio.AbstractEventLoop = asyncio.get_running_loop()
