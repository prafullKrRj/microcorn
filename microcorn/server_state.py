import asyncio
from dataclasses import dataclass, field


@dataclass
class ServerState:
    tasks: set[asyncio.Task[None]]
    connections: set[asyncio.Protocol]
    total_requests: int = 0
    application_state: dict[str, object] = field(default_factory=dict)

    def add_task(self, task: asyncio.Task[None]) -> None:
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def shutdown(self) -> None:
        for connection in tuple(self.connections):
            transport = getattr(connection, "transport", None)
            if transport is not None:
                transport.close()
        if self.tasks:
            await asyncio.gather(*tuple(self.tasks), return_exceptions=True)
