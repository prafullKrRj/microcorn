from asyncio import BaseProtocol
from typing import Callable

from microcorn.protocol.test_protocol import TestProtocol


def get_protocol_factory() -> Callable[[], BaseProtocol]:
    return TestProtocol
