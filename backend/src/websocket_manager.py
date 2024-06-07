import logging
from dataclasses import dataclass
from typing import List, Dict, Optional

from starlette.websockets import WebSocket

from .exceptions import AlreadySubscribed, NotInSubscriptions

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    key_prefix: str
    state: Optional[str] = None


class WebsocketManager:
    def __init__(self):
        self.connection_subscriptions: Dict[WebSocket, List[Subscription]] = {}  # TODO move this to Redis

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connection_subscriptions[websocket] = []

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connection_subscriptions:
            del self.connection_subscriptions[websocket]

    def subscribe(self, websocket: WebSocket, key_prefix: str):
        if next((s for s in self.connection_subscriptions[websocket] if s.key_prefix == key_prefix), None) is not None:
            raise AlreadySubscribed()
        self.connection_subscriptions[websocket].append(Subscription(key_prefix=key_prefix))

    def unsubscribe(self, websocket: WebSocket, key_prefix: str):
        if next((d for d in self.connection_subscriptions[websocket] if d.key_prefix == key_prefix), None) is None:
            raise NotInSubscriptions()
        self.connection_subscriptions[websocket] = [s for s in self.connection_subscriptions[websocket] if
                                                    s.key_prefix != key_prefix]

    async def broadcast(self, message: dict):  # sends all messages to all connections
        for conn in self.connection_subscriptions.keys():
            await conn.send_json(message)

    async def publish(self, message: dict):  # sends message to subscribed connections
        for conn, subscriptions in self.connection_subscriptions.items():
            for sub in subscriptions:
                for record in message.get("Records", []):
                    record_key = record["s3"]["object"]["key"]
                    if record_key.startswith(sub.key_prefix):
                        await conn.send_json(record)
                        break  # No need to check other prefixes if one matches (prefix is unique)


ws_manager = WebsocketManager()
