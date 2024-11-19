from unittest.mock import AsyncMock
import pytest
from redis.asyncio import Redis
from starlette.testclient import TestClient
import uuid
from typing import Tuple
from starlette.websockets import WebSocket

from src.settings import server_settings
from ...src.services.websocket_manager import WebsocketManager
from ...src.main import app


# @pytest.fixture(scope='session')
# def event_loop(request):
#     loop = asyncio.get_event_loop()
#     yield loop
#     loop.close()


@pytest.fixture
async def redis_client():
    redis_client = Redis.from_url(server_settings.CELERY_RESULT_BACKEND)
    yield redis_client
    await redis_client.aclose()


@pytest.fixture
async def manager_and_ws_connected(redis_client) -> Tuple[WebsocketManager, WebSocket]:
    test_client = TestClient(app=app)
    manager = WebsocketManager(redis_client)
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
    await manager.subscribe(ws, object_prefix=object_prefix)
    yield manager, ws, object_prefix
