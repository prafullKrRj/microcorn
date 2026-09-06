import asyncio
from dataclasses import dataclass


@dataclass
class ServerState:
    tasks: set[asyncio.Task[None]]
    connections: set[asyncio.Protocol]
    total_requests: int = 0
