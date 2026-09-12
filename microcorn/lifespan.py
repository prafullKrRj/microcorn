import asyncio
import logging
from asyncio import Queue
from typing import Any

from ._types import (
    ASGIVersions,
    LifespanScope,
    LifespanShutdownCompleteEvent,
    LifespanShutdownEvent,
    LifespanShutdownFailedEvent,
    LifespanStartupCompleteEvent,
    LifespanStartupEvent,
    LifespanStartupFailedEvent,
)

LifespanReceiveMessage = LifespanStartupEvent | LifespanShutdownEvent
LifespanSendMessage = (
    LifespanStartupFailedEvent
    | LifespanShutdownFailedEvent
    | LifespanStartupCompleteEvent
    | LifespanShutdownCompleteEvent
)
STATE_TRANSITION_ERROR = "Got invalid state transition on lifespan protocol."


class LifeSpan:
    def __init__(self, application=None, state: dict[str, Any] | None = None):
        self.application = application
        self.logger = logging.getLogger("microcorn.lifespan")
        self.state = state if state is not None else {}
        self.startup_event: asyncio.Event = asyncio.Event()
        self.shutdown_event: asyncio.Event = asyncio.Event()
        self.receive_queue: Queue[LifespanReceiveMessage] = asyncio.Queue()
        self.startup_failed = False
        self.shutdown_failed = False
        self.error_occurred = False
        self.should_exit = False

    async def startup(self) -> None:
        loop = asyncio.get_event_loop()
        loop.create_task(self.main())
        startup_event: LifespanStartupEvent = LifespanStartupEvent(
            type="lifespan.startup"
        )
        await self.receive_queue.put(startup_event)
        await self.startup_event.wait()

        if self.startup_failed or self.error_occurred:
            self.should_exit = True

    async def shutdown(self) -> None:
        if self.error_occurred:
            return
        shutdown_event: LifespanShutdownEvent = LifespanShutdownEvent(
            type="lifespan.shutdown"
        )
        await self.receive_queue.put(shutdown_event)
        await self.shutdown_event.wait()

        if self.shutdown_failed or self.error_occurred:
            self.should_exit = True

    async def main(self) -> None:
        try:
            scope: LifespanScope = {
                "type": "lifespan",
                "asgi": ASGIVersions(version="2.0", spec_version="2.3"),
                "state": self.state,
            }
            if self.application is None:
                await self.send({"type": "lifespan.startup.complete"})
                await self.receive()
                await self.send({"type": "lifespan.shutdown.complete"})
            else:
                await self.application(scope, self.receive, self.send)
                # Apps without lifespan support return without sending events.
                self.startup_event.set()
                self.shutdown_event.set()
        except Exception as ex:  # noqa: BLE001 - ASGI app errors become lifecycle failure
            self.error_occurred = True
            self.startup_event.set()
            self.shutdown_event.set()
            print(ex)

    async def send(self, message: LifespanSendMessage):
        assert message["type"] in (
            "lifespan.startup.complete",
            "lifespan.startup.failed",
            "lifespan.shutdown.complete",
            "lifespan.shutdown.failed",
        )

        if message["type"] == "lifespan.startup.complete":
            assert not self.startup_event.is_set(), STATE_TRANSITION_ERROR
            assert not self.shutdown_event.is_set(), STATE_TRANSITION_ERROR
            self.startup_event.set()

        elif message["type"] == "lifespan.startup.failed":
            assert not self.startup_event.is_set(), STATE_TRANSITION_ERROR
            assert not self.shutdown_event.is_set(), STATE_TRANSITION_ERROR
            self.startup_event.set()
            self.startup_failed = True
            if message.get("message"):
                self.logger.error(message["message"])

        elif message["type"] == "lifespan.shutdown.complete":
            assert self.startup_event.is_set(), STATE_TRANSITION_ERROR
            assert not self.shutdown_event.is_set(), STATE_TRANSITION_ERROR
            self.shutdown_event.set()

        elif message["type"] == "lifespan.shutdown.failed":
            assert self.startup_event.is_set(), STATE_TRANSITION_ERROR
            assert not self.shutdown_event.is_set(), STATE_TRANSITION_ERROR
            self.shutdown_event.set()
            self.shutdown_failed = True
            if message.get("message"):
                self.logger.error(message["message"])

    async def receive(self) -> LifespanReceiveMessage:
        return await self.receive_queue.get()
