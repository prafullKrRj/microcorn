from collections.abc import Iterable
from typing import Any, Literal, NotRequired, TypedDict


class ASGIVersions(TypedDict):
    spec_version: str
    version: Literal["2.0", "3.0"]


class RequestScope(TypedDict):
    # Protocol scope type; for HTTP request/response cycles this is always "http".
    type: Literal["http"]
    # ASGI specification and version supported by the server (see ASGIVersions).
    asgi: ASGIVersions
    # HTTP protocol version used by the client (e.g., "1.1", "2").
    http_version: str
    # HTTP request method in uppercase (e.g., "GET", "POST").
    method: str
    # URL scheme of the request: "http" or "https".
    scheme: str
    # URL path as a percent-decoded Unicode string (e.g., "/api/users").
    path: str
    # Original URL path as raw bytes, preserving percent-encoding exactly as received.
    raw_path: bytes
    # Query string portion of the URL as a string, without the leading "?".
    query_string: bytes
    # Root path prefix under which the application is mounted (often empty string).
    root_path: str
    # Request headers as an iterable of (header_name, header_value) byte tuples; names are lowercased.
    headers: Iterable[tuple[bytes, bytes]]
    # (host, port) of the client that initiated the request, or None if unavailable (e.g., unix socket).
    client: tuple[str, int] | None
    # (host, port) the server is listening on to which the client connected.
    server: tuple[str, int] | None
    # Optional application-defined state carried across the lifespan/requests.
    state: NotRequired[dict[str, Any]]
    # Optional ASGI extensions negotiated between server and application (extension name -> extension data).
    extensions: NotRequired[dict[str, dict[object, object]]]


class HTTPReceiveEvent(TypedDict):
    type: Literal["http.request"]
    body: bytes
    more_body: bool


class HTTPSendStartEvent(TypedDict):
    type: Literal["http.response.start"]
    status: int
    headers: NotRequired[Iterable[tuple[bytes, bytes]]]
    trailers: NotRequired[bool]


class HTTPSendResponseEvent(TypedDict):
    type: Literal["http.response.body"]
    body: bytes
    more_body: NotRequired[bool]


class LifespanScope(TypedDict):
    type: Literal["lifespan"]
    asgi: ASGIVersions
    state: NotRequired[dict[str, Any]]


class LifespanStartupEvent(TypedDict):
    type: Literal["lifespan.startup"]


class LifespanShutdownEvent(TypedDict):
    type: Literal["lifespan.shutdown"]


class LifespanStartupCompleteEvent(TypedDict):
    type: Literal["lifespan.startup.complete"]


class LifespanStartupFailedEvent(TypedDict):
    type: Literal["lifespan.startup.failed"]
    message: str


class LifespanShutdownCompleteEvent(TypedDict):
    type: Literal["lifespan.shutdown.complete"]


class LifespanShutdownFailedEvent(TypedDict):
    type: Literal["lifespan.shutdown.failed"]
    message: str


HTTPSendEvent = HTTPSendResponseEvent | HTTPSendStartEvent
