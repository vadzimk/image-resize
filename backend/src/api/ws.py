import json
import logging
import traceback
import uuid

from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect

from ..services.message_bus import bus
from ..services.handlers import command_handlers
from ..models.domain import commands
from ..services.websocket_manager import ws_manager
from ..utils import validate_message
from ..models.request.request_model import (
    SubscribeSchema,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Schema available in asyncapi docs (aysncapi.yaml, or asyncapi studio)
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Path/ws Client message {data}")
            message: dict = json.loads(data)
            bus.handle(make_command(message, websocket))
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception:
        logger.error(f"websocket_endpoint: error:\n{traceback.format_exc()}")
    finally:
        ws_manager.disconnect(websocket)


def make_command(message: dict, websocket: WebSocket) -> commands.Command:
    message_model = validate_message(message, [SubscribeSchema])
    for CommandType in command_handlers.keys():
        if CommandType.__name__.upper() == message_model.action:
            object_prefix_uuid = message_model.object_prefix if isinstance(message_model.object_prefix, uuid.UUID) \
                else uuid.UUID(message_model.object_prefix)
            command = CommandType(websocket, object_prefix_uuid)
            return command
    raise Exception(f"Unknown handler action {message_model.action}")
