import asyncio


class TransportFlow:
    def __init__(self, transport: asyncio.Transport) -> None:
        self.transport: asyncio.Transport = transport
        self.read_paused = False
        self.write_paused = False
        self.__writable_event: asyncio.Event = asyncio.Event()
        self.__writable_event.set()

    def drain(self) -> None:
        self.__writable_event.wait()

    def pause_reading(self) -> None:
        if not self.read_paused:
            self.read_paused = True
            self.transport.pause_reading()

    def resume_reading(self) -> None:
        if self.read_paused:
            self.read_paused = False
            self.transport.resume_reading()

    def pause_writing(self) -> None:
        if not self.write_paused:
            self.write_paused = True
            self.__writable_event.clear()

    def resume_writing(self) -> None:
        if self.write_paused:
            self.write_paused = False
            self.__writable_event.set()

    def write(self, data: bytes):
        self.transport.write(data)
