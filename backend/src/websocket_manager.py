import logging
from typing import List, Dict

from starlette.websockets import WebSocket

from .exceptions import AlreadySubscribed

logger = logging.getLogger(__name__)


class WebsocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[WebSocket, List[str]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = []

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]

    def subscribe(self, websocket: WebSocket, key_prefix: str):
        if key_prefix in self.subscriptions[websocket]:
            raise AlreadySubscribed()
        self.subscriptions[websocket].append(key_prefix)
        logger.debug(f'Subscribed to {key_prefix}')

    async def broadcast(self, message: dict):  # sends all messages to all connections
        for conn in self.active_connections:
            await conn.send_json(message)

    async def publish(self, message: dict):  # sends message to subscribed connections
        logger.debug("Entered def publish")
        logger.debug(self.subscriptions.items())
        for conn, key_prefixes in self.subscriptions.items():
            for key_prefix in key_prefixes:
                logger.debug(f'publish:key_prefix: {key_prefix}')
                for record in message.get("Records", []):
                    logger.debug(f'publish: record: {record}')
                    record_key = record["s3"]["object"]["key"]
                    logger.debug(f'publish: record_key: {record_key}')
                    logger.debug(f'Checking {record_key}.startswith({key_prefix}): {record_key.startswith(key_prefix)}')
                    if record["s3"]["object"]["key"].startswith(key_prefix):
                        logger.debug(f'Found {key_prefix}')
                        await conn.send_json(record)
                        break  # No need to check other prefixes if one matches (prefix is unique)


ws_manager = WebsocketManager()
