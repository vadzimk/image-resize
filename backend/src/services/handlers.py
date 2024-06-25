import asyncio
import logging
from asyncio import AbstractEventLoop
from typing import Dict, Type, List, Callable

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from starlette.websockets import WebSocket

from ..schemas import OnSubscribeSchema, SubscribeAction
from ..utils import validate_message
from ..exceptions import ClientError
from ..domain import events
from ..websocket_manager import ws_manager
from ..domain import commands

logger = logging.getLogger(__name__)


async def handle_ws_confirmation(action: Callable, initial_payload: dir, schema: Type[BaseModel], ws: WebSocket):
    initial_payload.update({"status_code": 200, "status": "OK"})
    try:
        action()
    except ClientError as err:
        initial_payload.update({"status_code": 400, "status": "Error", "message": str(err)})
    except Exception:
        raise
    finally:
        await ws.send_json(
            jsonable_encoder(
                validate_message(initial_payload, [schema])
            ))


def subscribe_handler(cmd: commands.Subscribe):
    loop = asyncio.get_running_loop()
    loop.create_task(
        handle_ws_confirmation(
            action=lambda: ws_manager.subscribe(cmd.websocket, cmd.project_id),
            initial_payload={"action": SubscribeAction.SUBSCRIBE, "project_id": cmd.project_id},
            schema=OnSubscribeSchema,
            ws=cmd.websocket))


def unsubscribe_handler(cmd: commands.Subscribe):
    loop = asyncio.get_running_loop()
    loop.create_task(
        handle_ws_confirmation(
            action=lambda: ws_manager.unsubscribe(cmd.websocket, cmd.project_id),
            initial_payload={"action": SubscribeAction.UNSUBSCRIBE, "project_id": cmd.project_id},
            schema=OnSubscribeSchema,
            ws=cmd.websocket))


def update_project_in_db(event: events.CeleryTaskUpdated):
    pass


def notify_subscribers(event: events.CeleryTaskUpdated):
    logger.info(f"handler:notify_subscribers:event: {event}")
    asyncio.run_coroutine_threadsafe(ws_manager.publish_celery_event(event.message), loop=event.loop)


event_handlers: Dict[Type[events.Event], List[Callable]] = {
    events.CeleryTaskUpdated: [update_project_in_db, notify_subscribers],
}

command_handlers: Dict[Type[commands.Command], Callable] = {
    commands.Subscribe: subscribe_handler,
    commands.UnSubscribe: unsubscribe_handler,
}
