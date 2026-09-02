from asyncio import BaseProtocol


class TestProtocol(BaseProtocol):
    def __init__(self):
        super().__init__()

    def connection_made(self, transport: transports.BaseTransport) -> None:
        super().connection_made()

    def connection_lost(self, exc: Exception | None) -> None:
        super().connection_lost()

    def pause_writing(self) -> None:
        super().pause_writing()

    def resume_writing(self) -> None:
        super().resume_writing()
