import logging
from dataclasses import dataclass
from typing import List, Dict, Optional

from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocket

from .utils import validate_message
from .schemas import ProjectProgressSchema, GetProjectSchema, ProjectFailureSchema
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
        logger.info(f"WebsocketManager.subscribe: {websocket}, {key_prefix}")
        if next((s for s in self.connection_subscriptions[websocket] if s.key_prefix == key_prefix), None) is not None:
            raise AlreadySubscribed()
        self.connection_subscriptions[websocket].append(Subscription(key_prefix=key_prefix))
        logger.debug(f"self.connection_subscriptions {self.connection_subscriptions}")

    def unsubscribe(self, websocket: WebSocket, key_prefix: str):
        if next((d for d in self.connection_subscriptions[websocket] if d.key_prefix == key_prefix), None) is None:
            raise NotInSubscriptions()
        self.connection_subscriptions[websocket] = [s for s in self.connection_subscriptions[websocket] if
                                                    s.key_prefix != key_prefix]

    async def publish_celery_event(self, message: ProjectProgressSchema | GetProjectSchema | ProjectFailureSchema):
        logger.debug(f"publish_celery_event: message {message} {type(message)}")
        for conn, subscriptions in self.connection_subscriptions.items():
            for sub in subscriptions:
                logger.debug(f"===???? {message.project_id} {message.project_id == sub.key_prefix} {sub.key_prefix}")
                if str(message.project_id) == sub.key_prefix:
                    logger.debug(f"sending =====> {message}")
                    await conn.send_json(
                        jsonable_encoder(
                            validate_message(message, [ProjectProgressSchema, GetProjectSchema, ProjectFailureSchema])
                        ))
                    break


ws_manager = WebsocketManager()
