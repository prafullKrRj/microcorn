from asyncio import Event
from typing import Union

import h11
from h11 import NEED_DATA, PAUSED, RemoteProtocolError

from microcorn.protocol.transport_flow import TransportFlow

EventType = Union[Event, type[NEED_DATA], type[PAUSED]]


class EventHandler:
    def __init__(self, conn: h11.Connection, flow: TransportFlow):
        self.conn: h11.Connection = conn
        self.flow = flow
        self.body = ""

    def handle_events(self):
        while True:
            try:
                event: EventType = self.conn.next_event()
            except RemoteProtocolError:
                print("remote protocol error")
                return
            if event is NEED_DATA:
                return
            elif event is PAUSED:
                self.flow.pause_reading()
                break

            elif isinstance(event, h11.Request):
                headers = event.headers
                print(event.target)
                print(event.headers)
                print(event.method)

            elif isinstance(event, h11.Data):
                self.body += event.data.decode("utf-8")
                print(self.body)

            elif isinstance(event, h11.EndOfMessage):
                response_body = (
                    f"Echoed request body:\n{self.body}\nMethod: {self.conn.our_role}\n"
                ).encode("utf-8")
                h11_response = h11.Response(
                    status_code=200,
                    headers=[
                        (b"content-type", b"text/plain"),
                        (b"server", b"microcorn-test"),
                        (b"x-test-header", b"random-value-123"),
                        (b"content-length", str(len(response_body)).encode("ascii")),
                    ],
                )
                output = self.conn.send(event=h11_response)
                self.flow.write(output)
                output = self.conn.send(event=h11.Data(data=response_body))
                self.flow.write(output)
                output = self.conn.send(event=h11.EndOfMessage())
                self.flow.write(output)
                self.body = ""
                break


"""
Sample headers:
<Headers([(b'postman-token', b'2d39be20-48df-422e-ad04-5fb762812ffb'), (b'host', b'localhost:8080'), (b'user-agent', b'PostmanRuntime/2.5.0'), (b'accept', b'*/*'), (b'accept-encoding', b'gzip, deflate, br'), (b'connection', b'keep-alive')])>


With Params:
'/?abc=12'
<Headers([(b'postman-token', b'88027011-b18b-43a3-abeb-a10a686b7824'), (b'content-type', b'application/json'), (b'content-length', b'25'), (b'host', b'localhost:8080'), (b'user-agent', b'PostmanRuntime/2.5.0'), (b'accept', b'*/*'), (b'accept-encoding', b'gzip, deflate, br'), (b'connection', b'keep-alive')])>


Sample Body:
b'POST'
{
    "Name": "Prafull"
}


"""
