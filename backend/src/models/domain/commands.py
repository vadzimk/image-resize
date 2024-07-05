import uuid
from dataclasses import dataclass

from starlette.websockets import WebSocket


class Command:
    pass


@dataclass
class Subscribe(Command):
    websocket: WebSocket
    object_prefix: uuid.UUID


@dataclass
class UnSubscribe(Command):
    websocket: WebSocket
    object_prefix: uuid.UUID
