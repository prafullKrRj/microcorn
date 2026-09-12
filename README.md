# microcorn

Small ASGI server I'm building.

## Run a Starlette app

Install package in your application environment, then run target from that application's directory:

```bash
uv add /path/to/microcorn
microcorn main:app
```

`main.py` must expose a callable ASGI app, for example:

```python
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

async def homepage(request):
    return PlainTextResponse("Hello from Starlette")

app = Starlette(routes=[Route("/", homepage)])
```

Useful options: `--host`, `--port`, `--workers`, and `--app-dir`.

## What is ASGI?

**ASGI** (Asynchronous Server Gateway Interface) is the Python standard interface between async-capable web servers and Python web applications/frameworks.

It's the async successor to **WSGI**:

- **WSGI** — one request at a time, synchronous; app is a callable receiving `(environ, start_response)`.
- **ASGI** — async, supports long-lived connections (HTTP/1.1, HTTP/2, WebSockets); app is an `async` function receiving `(scope, receive, send)`.

### High-level

An ASGI app is an `async` callable:

```python
async def app(scope, receive, send):
    # scope   -> connection metadata (type, path, headers, ...)
    # receive -> async fn to await incoming events/messages
    # send    -> async fn to send events/messages back
    ...
```

Three call shapes cover most use:

- **HTTP** — `scope["type"] == "http"`, exchange request/response messages.
- **WebSocket** — `scope["type"] == "websocket"`, exchange text/binary frames.
- **Lifespan** — `scope["type"] == "lifespan"`, server sends startup/shutdown events to the app.

The server (e.g. `uvicorn`) handles the raw socket, HTTP parsing, and protocol details; the app just consumes events and emits events. That decoupling lets the same app run on different servers and lets servers host different apps without either side knowing the other's internals.
