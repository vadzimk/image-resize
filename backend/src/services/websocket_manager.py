import json
import logging
import uuid
from dataclasses import dataclass
from typing import List, Dict

from fastapi.encoders import jsonable_encoder
from redis.asyncio import Redis
from starlette.websockets import WebSocket

from .message_broker import redis_client
from .minio import get_presigned_url_get

from ..utils import validate_message
from ..models.request.request_model import ProjectProgressSchema, GetProjectSchema, ProjectFailureSchema
from ..exceptions import AlreadySubscribed, NotInSubscriptions

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    object_prefix: uuid.UUID

    def to_dict(self):
        return {
            "object_prefix": str(self.object_prefix),  # Convert UUID to string
        }

    @classmethod
    def from_dict(cls, data):
        return cls(object_prefix=uuid.UUID(data["object_prefix"]))


class WebsocketManager:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.redis_key_prefix = 'websocket'
        self.local_websockets: Dict[
            str, WebSocket] = {}  # each server in the pool handles its local connections and listens for events in redis pub/sub

    async def connect(self, websocket: WebSocket):
        websocket_id = str(websocket)
        self.local_websockets[websocket_id] = websocket
        await websocket.accept()
        logger.info(f"WS Client connected {websocket_id}")

    async def disconnect(self, websocket: WebSocket):
        websocket_id = str(websocket)
        if websocket_id in self.local_websockets:
            del self.local_websockets[websocket_id]

        pattern = self._make_redis_key(websocket, object_prefix='*')
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

    async def subscribe(self, websocket: WebSocket, object_prefix: uuid.UUID):
        if not isinstance(object_prefix, uuid.UUID):
            raise Exception(f"object_prefix must be of type UUID but got {type(object_prefix)}")
        logger.debug(f"websocket: {websocket}, object_prefix: {object_prefix}")
        key = self._make_redis_key(websocket, object_prefix)
        exists = await self.redis.exists(key)
        if exists:
            raise AlreadySubscribed()
        await self.redis.set(key, json.dumps(Subscription(object_prefix=object_prefix).to_dict()))

    async def unsubscribe(self, websocket: WebSocket, object_prefix: uuid.UUID):
        key = self._make_redis_key(websocket, object_prefix)
        exists = await self.redis.exists(key)
        if not exists:
            raise NotInSubscriptions()
        await self.redis.delete(key)

    async def _publish(self, object_prefix: uuid.UUID, message: dict):
        """
        publish event to redis pub/sub channel
        responsible for broadcasting the event to all servers in the pool
        """
        await self.redis.publish(f'events:{object_prefix}', json.dumps(message))

    async def handle_pubsub_events(self):
        """
        subscribes servers in the pool to redis Pub/Sub channel
        must run as separate task after server startup
        """
        pubsub = self.redis.pubsub()
        await pubsub.psubscribe(f'events:*')
        logger.info('Subscribed to Pub/Sub events')

        async for message in pubsub.listen():
            if message['type'] == 'pmessage':
                channel = message['channel'].decode()
                object_prefix = channel.split(':')[1]
                payload = json.loads(message['data'].decode())
                await self._dispatch_event(object_prefix, payload)

    async def _dispatch_event(self, object_prefix: str, payload: dict):
        """ find all subscriptions for this object_prefix """
        pattern = self._make_redis_key(websocket='*', object_prefix=object_prefix)
        keys = await self.redis.keys(pattern)
        for key in keys:
            key_str = key.decode()
            websocket_id = key_str.split(':')[1]
            if websocket_id in self.local_websockets:
                websocket = self.local_websockets[websocket_id]
                try:
                    await websocket.send_json(payload)
                except Exception as e:
                    logger.error(f'Failed to send message to {websocket_id}: {e}')
                    await self.disconnect(websocket)

    def _make_redis_key(self, websocket: WebSocket | str, object_prefix: uuid.UUID | str):
        return f'{self.redis_key_prefix}:{websocket}:subscription:{object_prefix}'

    async def _get_subscriptions(self, websocket: WebSocket) -> List[dict]:
        pattern = self._make_redis_key(websocket, object_prefix='*')
        keys = await self.redis.keys(pattern)
        subscriptions = []
        for key in keys:
            subscription = await self.redis.get(key)
            subscriptions.append(json.loads(subscription))
        return subscriptions

    async def publish_celery_event(self, message: ProjectProgressSchema | GetProjectSchema | ProjectFailureSchema):
        logger.debug(f"message: {message}, message type: {type(message)}")

        # First, notify other servers in the pool by publishing the event to Redis
        await self._publish(message.object_prefix, jsonable_encoder(message))

        pattern = self._make_redis_key(websocket='*', object_prefix='*')
        keys = await self.redis.keys(pattern)
        for key in keys:
            key_str = key.decode()
            _, websocket_id, _, object_prefix = key_str.split(':')
            if websocket_id in self.local_websockets:
                websocket = self.local_websockets[websocket_id]
                if str(object_prefix) == str(message.object_prefix):
                    logger.debug(f"Sending message: `{message}` to {websocket_id}")
                    message.versions = {key: get_presigned_url_get(value) for key, value in message.versions.items()}
                    await websocket.send_json(
                        jsonable_encoder(
                            validate_message(message, [ProjectProgressSchema, GetProjectSchema, ProjectFailureSchema])
                        ))


ws_manager = WebsocketManager(redis_client)
