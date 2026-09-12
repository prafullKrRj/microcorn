import argparse
import importlib
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def load_target(target: str) -> Any:
    if not isinstance(target, str) or not target.strip():
        raise ValueError("Application target must be a non-empty string")
    if ":" not in target:
        raise ValueError("Application target must use 'module:attribute' format")
    module_name, attribute_path = (part.strip() for part in target.split(":", 1))
    if not module_name or not attribute_path:
        raise ValueError("Application target must use 'module:attribute' format")
    try:
        application: Any
        module_path = Path(module_name)
        if module_path.suffix == ".py" and module_path.exists():
            spec = importlib.util.spec_from_file_location(
                f"microcorn_target_{module_path.stem}", module_path
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load module file '{module_path}'")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            application = module
        else:
            application = importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        raise ImportError(f"Could not import module '{module_name}'") from error
    for attribute in attribute_path.split("."):
        if not hasattr(application, attribute):
            raise AttributeError(
                f"Module '{module_name}' has no attribute '{attribute_path}'"
            )
        application = getattr(application, attribute)
    if not callable(application):
        raise TypeError(f"Application target '{target}' is not callable")
    return application


@dataclass
class Config:
    target: str
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 1
    reload: bool = False
    app_dir: str | None = None
    application: Any | None = None

    def load(self) -> Any:
        if self.workers < 1:
            raise ValueError("workers must be at least 1")
        if self.reload and self.workers > 1:
            raise ValueError("--reload cannot be combined with --workers")
        app_dir = Path(self.app_dir).resolve() if self.app_dir else Path.cwd()
        if app_dir:
            app_dir = str(app_dir)
            if app_dir not in sys.path:
                sys.path.insert(0, app_dir)
        self.application = load_target(self.target)
        return self.application


def run(
    application: Any,
    host: str,
    port: int,
    workers: int = 1,
    *,
    target: str | None = None,
) -> None:
    from microcorn.server import MicroCornServer

    if workers < 1:
        raise ValueError("workers must be at least 1")
    if workers == 1:
        MicroCornServer(application=application, host=host, port=port).run()
        return
    if target is None:
        raise ValueError("target is required when workers is greater than 1")
    from microcorn.workers import Multiprocess

    Multiprocess(target=target, host=host, port=port, workers=workers).run()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="microcorn",
        description="A small Python application server",
    )

    parser.add_argument(
        "target",
        help="Application target, for example main:app",
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to",
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="Reload when source files change",
    )
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    parser.add_argument("--app-dir", help="Directory to add to Python import path")

    args = parser.parse_args()

    try:
        config = Config(
            target=args.target,
            host=args.host,
            port=args.port,
            workers=args.workers,
            reload=args.reload,
            app_dir=args.app_dir,
        )
        application = config.load()
    except (ImportError, AttributeError, TypeError, ValueError) as error:
        parser.error(str(error))

    if args.reload:
        print("Reload mode enabled")

    run(application, args.host, args.port, args.workers, target=args.target)


if __name__ == "__main__":
    main()
