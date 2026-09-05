from asyncio import BaseProtocol
from typing import Callable

from microcorn.protocol.h11 import H11Protocol


def get_protocol_factory() -> Callable[[], BaseProtocol]:
    return H11Protocol
