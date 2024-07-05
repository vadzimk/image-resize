import asyncio
import uuid
from typing import Tuple
from unittest.mock import AsyncMock

import pytest
from fastapi.encoders import jsonable_encoder
from starlette.testclient import TestClient
from starlette.websockets import WebSocket

from ...src.utils import validate_message
from ...src.models.request.request_model import GetProjectSchema, TaskState
from ...src.main import app
from ...src.services.websocket_manager import WebsocketManager


@pytest.fixture
async def manager_and_ws_connected() -> Tuple[WebsocketManager, WebSocket]:
    test_client = TestClient(app=app)
    manager = WebsocketManager()
    ws = test_client.websocket_connect("/ws")  # also can be used as context manager
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock(side_effect=ws.send_json)
    await manager.connect(ws)

    yield manager, ws

    ws.close()


@pytest.fixture
async def subscribed(manager_and_ws_connected) -> Tuple[WebsocketManager, WebSocket, uuid.UUID]:
    manager, ws = manager_and_ws_connected
    object_prefix = uuid.uuid4()
    manager.subscribe(ws, object_prefix=object_prefix)
    return manager, ws, object_prefix


class TestConnection:
    async def test_can_connect(self, manager_and_ws_connected):
        manager, _ = manager_and_ws_connected
        assert len(manager.connection_subscriptions.keys()) == 1

    async def test_can_disconnect(self, manager_and_ws_connected):
        manager, ws = manager_and_ws_connected
        manager.disconnect(ws)
        assert len(manager.connection_subscriptions) == 0


class TestSubscription:
    async def test_can_subscribe(self, subscribed):
        manager, ws, object_prefix = subscribed
        assert manager.connection_subscriptions.get(ws)[0].object_prefix == object_prefix

    async def test_can_unsubscribe(self, subscribed):
        manager, ws, object_prefix = subscribed
        manager.unsubscribe(ws, object_prefix)
        assert len(manager.connection_subscriptions.get(ws)) == 0


async def test_can_publish_celery_event(subscribed: Tuple[WebsocketManager, WebSocket, uuid.UUID]):
    manager, ws, object_prefix = subscribed
    message = GetProjectSchema(object_prefix=object_prefix, state=TaskState.SUCCESS, versions={})
    await manager.publish_celery_event(message)
    ws.send_json.assert_called_once()
    ws.send_json.assert_called_with(jsonable_encoder(
        validate_message(message, [GetProjectSchema])
    ))

