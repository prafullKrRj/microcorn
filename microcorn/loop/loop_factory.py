import asyncio
from collections.abc import Callable


def get_loop_factory() -> Callable[[], asyncio.AbstractEventLoop]:
    try:
        import uvloop

        return uvloop.new_event_loop
    except ImportError:
        return asyncio.SelectorEventLoop
