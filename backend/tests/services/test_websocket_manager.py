import uuid
from typing import Tuple
from unittest.mock import MagicMock, AsyncMock

from redis.asyncio import Redis
from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocket

from src.settings import server_settings
from ...src.utils import validate_message
from ...src.models.request.request_model import GetProjectSchema, TaskState
from ...src.services.websocket_manager import WebsocketManager


class TestConnection:
    async def test_can_connect(self, manager_and_ws_connected):
        manager, ws = manager_and_ws_connected
        assert len(manager.local_websockets.keys()) == 1

    async def test_can_disconnect(self, manager_and_ws_connected):
        manager, ws = manager_and_ws_connected
        await manager.disconnect(ws)
        assert len(manager.local_websockets.keys()) == 0


class TestSubscription:
    async def test_can_subscribe(self, subscribed, redis_client):
        manager, ws, object_prefix = subscribed
        key = manager._make_redis_key(ws, object_prefix)
        assert await redis_client.exists(key), "After subscribe, the Key was not found in Redis, but was expected"

    async def test_can_unsubscribe(self, subscribed, redis_client):
        manager, ws, object_prefix = subscribed
        key = manager._make_redis_key(ws, object_prefix)
        assert await redis_client.exists(key), "After subscribe, the Key was not found in Redis, but was expected"
        await manager.unsubscribe(ws, object_prefix)
        assert not await redis_client.exists(key), "After unsubscribe, the Key was found in Redis, but was not expected"


async def test_can_publish_celery_event(subscribed: Tuple[WebsocketManager, WebSocket, uuid.UUID]):
    manager, ws, object_prefix = subscribed
    ws.send_json = AsyncMock()
    message = GetProjectSchema(object_prefix=object_prefix, state=TaskState.SUCCESS, versions={})
    await manager.publish_celery_event(message)
    ws.send_json.assert_called_once()
    ws.send_json.assert_called_with(jsonable_encoder(
        validate_message(message, [GetProjectSchema])
    ))
