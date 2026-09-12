import multiprocessing
import socket


def _worker_main(target: str, host: str, port: int, sock: socket.socket) -> None:
    from microcorn.config import Config
    from microcorn.server import MicroCornServer

    application = Config(target=target, host=host, port=port).load()
    MicroCornServer(application, host, port).run(sock)


class Multiprocess:

    def __init__(self, target: str, host: str, port: int, workers: int):
        self.target = target
        self.host = host
        self.port = port
        self.workers = workers
        self.processes: list[multiprocessing.Process] = []

    def run(self) -> None:
        context = multiprocessing.get_context("spawn")
        with socket.create_server((self.host, self.port), reuse_port=False) as sock:
            self.processes = [
                context.Process(
                    target=_worker_main,
                    args=(self.target, self.host, self.port, sock),
                )
                for _ in range(self.workers)
            ]
            for process in self.processes:
                process.start()
            try:
                for process in self.processes:
                    process.join()
            except KeyboardInterrupt:
                for process in self.processes:
                    process.terminate()
                for process in self.processes:
                    process.join()
