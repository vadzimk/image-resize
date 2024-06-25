import asyncio
import json
import logging
from typing import Dict, Type, List, Callable

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from starlette.websockets import WebSocket

from ..repository.projects_repository import ProjectsRepository
from ..repository.uow import UnitOfWork
from .projects_service import ProjectsService
from ..schemas import OnSubscribeSchema, SubscribeAction, ImageVersion
from ..utils import validate_message
from ..exceptions import ClientError, ProjectNotFoundError
from ..domain import events
from ..websocket_manager import ws_manager
from ..domain import commands
from ..worker import create_versions

logger = logging.getLogger(__name__)


async def update_project_in_db(project_id: str, update: dict):
    logger.info(f"about to update_project_in_db: {type(project_id)} {project_id} | {type(update)} {update}")
    try:
        async with UnitOfWork() as uow:
            repository = ProjectsRepository(uow.session)
            projects_service = ProjectsService(repository)
            updated = await projects_service.update_project(project_id, update)
            await uow.commit()
            logger.info(f"update_project_in_db: {updated.dict()}")
    except ProjectNotFoundError as e:
        logger.error(e)


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


def update_project(event: events.CeleryTaskUpdated | events.OriginalUploaded):
    update = event.message.model_dump_json()
    logger.info(f"update_project:update: {update}")
    asyncio.run_coroutine_threadsafe(update_project_in_db(
        project_id=str(event.message.project_id),
        update=json.loads(event.message.model_dump_json())
    ), loop=event.loop)


def notify_subscribers(event: events.CeleryTaskUpdated):
    logger.info(f"handler:notify_subscribers:event: {event}")
    asyncio.run_coroutine_threadsafe(
        ws_manager.publish_celery_event(event.message), loop=event.loop)


def start_celery_task(event: events.OriginalUploaded):
    celery_task = create_versions.s(
        object_name_original=event.message.versions.get(ImageVersion.original)).apply_async()
    result = celery_task.get()
    logger.info(
        f"listen_create_s3_events_to_upload_versions: Celery task created task-id: {celery_task.id}, result: {result}")


event_handlers: Dict[Type[events.Event], List[Callable]] = {
    events.CeleryTaskUpdated: [update_project, notify_subscribers],
    events.OriginalUploaded: [update_project, start_celery_task]
}

command_handlers: Dict[Type[commands.Command], Callable] = {
    commands.Subscribe: subscribe_handler,
    commands.UnSubscribe: unsubscribe_handler,
}
