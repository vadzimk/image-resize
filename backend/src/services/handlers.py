import logging
import traceback
from typing import Dict, Type, List, Callable

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from starlette.websockets import WebSocket

from ..repository.projects_repository import ProjectsRepository
from ..repository.uow import UnitOfWork
from .projects_service import ProjectsService
from ..models.request.request_model import OnSubscribeSchema, SubscribeAction, ImageVersion, TaskState
from ..utils import validate_message
from ..exceptions import ClientError, ProjectNotFoundError
from ..models.domain import events
from ..websocket_manager import ws_manager
from ..models.domain import commands
from ..worker import create_versions

logger = logging.getLogger(__name__)


async def update_project_in_db(project_id: str, update: dict):
    logger.debug(f"about to update_project_in_db: {type(project_id)} {project_id} | {type(update)} {update}")
    try:
        async with UnitOfWork() as uow:
            repository = ProjectsRepository(uow.session)
            projects_service = ProjectsService(repository)
            updated = await projects_service.update_project(project_id, update)
            await uow.commit()
            logger.debug(f"update_project_in_db: {updated.dict()}")
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


async def subscribe_handler(cmd: commands.Subscribe):
    await handle_ws_confirmation(
        action=lambda: ws_manager.subscribe(cmd.websocket, cmd.project_id),
        initial_payload={"action": SubscribeAction.SUBSCRIBE, "project_id": cmd.project_id},
        schema=OnSubscribeSchema,
        ws=cmd.websocket)


async def unsubscribe_handler(cmd: commands.Subscribe):
    await handle_ws_confirmation(
        action=lambda: ws_manager.unsubscribe(cmd.websocket, cmd.project_id),
        initial_payload={"action": SubscribeAction.UNSUBSCRIBE, "project_id": cmd.project_id},
        schema=OnSubscribeSchema,
        ws=cmd.websocket)


async def update_project_handler(event: events.CeleryTaskUpdated | events.OriginalUploaded):
    update = event.message.model_dump()
    logger.debug(f"update_project:update: {update}")
    await update_project_in_db(
        project_id=str(event.message.project_id),
        update=update
    )


async def update_failed_project_handler(event: events.CeleryTaskFailed):
    logger.debug(f"handling failed project event {event}")
    try:
        async with UnitOfWork() as uow:
            repository = ProjectsRepository(uow.session)
            projects_service = ProjectsService(repository)
            [project, *_] = await projects_service.list_projects(filters={"celery_task_id": event.message.task_id})
            updated = await projects_service.update_project(project.project_id, update=event.message.model_dump())
            await uow.commit()
            logger.debug(f"update failed project in db {updated}")
    except Exception:
        logger.error(f"Unexpected error:\n{traceback.format_exc()}")
        raise


async def notify_subscribers_handler(event: events.CeleryTaskUpdated | events.CeleryTaskFailed):
    logger.debug(f"handler:notify_subscribers:event: {event}")
    await ws_manager.publish_celery_event(event.message)


async def start_celery_task_handler(event: events.OriginalUploaded):
    celery_task = create_versions.s(
        object_name_original=event.message.versions.get(ImageVersion.original)).apply_async()
    logger.debug(
        f"listen_create_s3_events_to_upload_versions: Celery task created task-id: {celery_task.id}")
    await update_project_in_db(event.message.project_id,
                               {
                                   "state": TaskState.STARTED,
                                   "celery_task_id": celery_task.id
                               })


event_handlers: Dict[Type[events.Event], List[Callable]] = {
    events.CeleryTaskUpdated: [update_project_handler, notify_subscribers_handler],
    events.OriginalUploaded: [update_project_handler, start_celery_task_handler],
    events.CeleryTaskFailed: [update_failed_project_handler, notify_subscribers_handler]
}

command_handlers: Dict[Type[commands.Command], Callable] = {
    commands.Subscribe: subscribe_handler,
    commands.UnSubscribe: unsubscribe_handler,
}
