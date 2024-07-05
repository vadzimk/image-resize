import logging
import uuid
from dataclasses import dataclass
from typing import List, Dict

from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocket

from ..utils import validate_message
from ..models.request.request_model import ProjectProgressSchema, GetProjectSchema, ProjectFailureSchema
from ..exceptions import AlreadySubscribed, NotInSubscriptions

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    object_prefix: uuid.UUID


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

    def subscribe(self, websocket: WebSocket, object_prefix: uuid.UUID):
        if not isinstance(object_prefix, uuid.UUID):
            raise Exception(f"object_prefix must be of type UUID but got {type(object_prefix)}")
        logger.debug(f"WebsocketManager.subscribe: {websocket}, {object_prefix}")
        if next((s for s in self.connection_subscriptions[websocket] if s.object_prefix == object_prefix),
                None) is not None:
            raise AlreadySubscribed()
        self.connection_subscriptions[websocket].append(Subscription(object_prefix=object_prefix))
        logger.debug(f"self.connection_subscriptions {self.connection_subscriptions}")

    def unsubscribe(self, websocket: WebSocket, object_prefix: uuid.UUID):
        if next((d for d in self.connection_subscriptions[websocket] if d.object_prefix == object_prefix),
                None) is None:
            raise NotInSubscriptions()
        self.connection_subscriptions[websocket] = [s for s in self.connection_subscriptions[websocket] if
                                                    s.object_prefix != object_prefix]

    async def publish_celery_event(self, message: ProjectProgressSchema | GetProjectSchema | ProjectFailureSchema):
        logger.debug(f"publish_celery_event: message {message} {type(message)}")
        for conn, subscriptions in self.connection_subscriptions.items():
            for sub in subscriptions:
                logger.debug(
                    f"publish_celery_event:sub {message.object_prefix} {message.object_prefix == sub.object_prefix} {sub.object_prefix}")
                if message.object_prefix == sub.object_prefix:
                    logger.debug(f"sending `{message}` to {conn} {type(conn)}")
                    await conn.send_json(
                        jsonable_encoder(
                            validate_message(message, [ProjectProgressSchema, GetProjectSchema, ProjectFailureSchema])
                        ))
                    break


ws_manager = WebsocketManager()
