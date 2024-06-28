from dataclasses import dataclass

from starlette.websockets import WebSocket


class Command:
    pass


@dataclass
class Subscribe(Command):
    websocket: WebSocket
    project_id: str


@dataclass
class UnSubscribe(Command):
    websocket: WebSocket
    project_id: str
