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
        self.connection_subscriptions: Dict[WebSocket, List[Subscription]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        logger.info(f"WS Client connected {websocket}")
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
        connections = list(self.connection_subscriptions.keys())
        logger.info(f"Entered async broadcast, connections_length: {len(connections)}: {connections}")
        for conn in connections:
            try:
                await conn.send_json(message)
                logger.info(f"Sent Broadcast to {conn} : {message}")
            except Exception as e:
                logger.error(e)
                raise e

    async def publish_s3_event(self, message: dict):  # sends message to subscribed connections
        for conn, subscriptions in self.connection_subscriptions.items():
            for sub in subscriptions:
                for record in message.get("Records", []):
                    record_key = record["s3"]["object"]["key"]
                    if record_key.startswith(sub.key_prefix):
                        await conn.send_json(record)
                        break  # No need to check other prefixes if one matches (prefix is unique)

    async def publish_celery_event(self, message: dict):
        for conn, subscriptions in self.connection_subscriptions.items():
            for sub in subscriptions:
                if message.get("project_id") == sub.key_prefix:
                    await conn.send_json(message)
                    break


ws_manager = WebsocketManager()
