import json
import logging
import traceback
import uuid
from typing import Type, Union

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from starlette import status
from starlette.websockets import WebSocket, WebSocketDisconnect

from .domain.commands import UnSubscribe, Subscribe, Command
from .services.handlers import command_handlers
from .bootstrap import bootstrap
from .domain import commands
from .services.message_bus import Message
from .services.minio import get_presigned_url_get
from .repository.uow import UnitOfWork
from .repository.projects_repository import ProjectsRepository
from .services.projects_service import ProjectsService
from .exceptions import ClientError
from .websocket_manager import ws_manager
from .schemas import (ProjectCreatedSchema,
                      CreateProjectSchema,
                      GetProjectSchema,
                      SubscribeSchema,
                      OnSubscribeSchema,
                      GetProjectsSchema,
                      SubscribeAction,
                      )

from .utils import validate_message

router = APIRouter()
logger = logging.getLogger(__name__)
bus = bootstrap()


def s3_object_names_to_urls(versions: dict) -> dict:
    """ return new versions dict with s3 object names replaced by s3 get_urls """
    result = versions.copy()
    for key, value in result.items():
        result[key] = get_presigned_url_get(value)
    return result


@router.post("/images", response_model=ProjectCreatedSchema, status_code=status.HTTP_201_CREATED)
async def get_new_image_url(create_project: CreateProjectSchema):
    """
    Generate a new image upload url
    """
    async with UnitOfWork() as uow:
        repository = ProjectsRepository(uow.session)
        project_service = ProjectsService(repository)
        project_dom = await project_service.create_project(create_project)
        await uow.commit()

    return ProjectCreatedSchema(
        filename=create_project.filename,
        project_id=project_dom.project_id,
        upload_link=project_dom.pre_signed_url
    )


@router.get("/projects/{project_id}", response_model=GetProjectSchema)
async def get_project(project_id: uuid.UUID):
    async with UnitOfWork() as uow:
        repository = ProjectsRepository(uow.session)
        projects_service = ProjectsService(repository)
        project = await projects_service.get_project(project_id)
        return GetProjectSchema(
            project_id=project.project_id,
            state=project.state,
            versions=s3_object_names_to_urls(project.versions)
        )


@router.get("/projects", response_model=GetProjectsSchema)
async def get_projects(skip: int = 0, limit: int = 10):
    async with UnitOfWork() as uow:
        repository = ProjectsRepository(uow.session)
        project_service = ProjectsService(repository)
        projects = await project_service.list_projects(skip=skip, limit=limit)
        return GetProjectsSchema(
            projects=[
                GetProjectSchema(
                    project_id=proj.project_id,
                    state=proj.state,
                    versions=s3_object_names_to_urls(proj.versions)
                ) for proj in projects])


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
            # await handle_message(websocket, message)  # TODO remove it, this is the old way
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
            return CommandType(websocket, str(message_model.project_id))
    raise Exception(f"Unknown handler action {message_model.action}")


# async def handle_message(websocket: WebSocket, message: dict):
#     """
#     validates websocket incoming messages and passes them to ws_manager
#     """
#     logger.debug("Enter handle_message")
#     message_model = validate_message(message, [SubscribeSchema])
#     logger.debug(f"handle_message message_model {message_model}")
#     response_message = message_model.model_dump()
#     response_message.update({"status_code": 200, "status": "OK"})
#     try:
#         if isinstance(message_model, SubscribeSchema):
#             if message_model.action == SubscribeAction.SUBSCRIBE:
#                 ws_manager.subscribe(websocket, str(message_model.project_id))
#                 logger.debug(f"Subscribed")
#             elif message_model.action == SubscribeAction.UNSUBSCRIBE:
#                 ws_manager.unsubscribe(websocket, str(message_model.project_id))
#                 logger.warning(f"Unsubscribed")
#             else:
#                 raise Exception(f"Unknown SubscribeAction: {message_model.action}")
#         else:
#             raise Exception(f"handle_message: unexpected Pydantic Model {type(message_model).__name__}")
#     except ClientError as err:
#         response_message.update({"status_code": 400, "status": "Error", "message": str(err)})
#     except Exception:
#         raise
#     finally:
#         await websocket.send_json(
#             jsonable_encoder(
#                 validate_message(response_message, [OnSubscribeSchema])
#             ))
