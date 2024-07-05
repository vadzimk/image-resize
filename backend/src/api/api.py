import json
import logging
import traceback
import uuid
from typing import List

from fastapi import APIRouter
from starlette import status
from starlette.websockets import WebSocket, WebSocketDisconnect

from ..services.message_bus import bus
from ..models.domain.object_model import ProjectDOM
from ..services.handlers import command_handlers
from ..models.domain import commands
from ..services.minio import get_presigned_url_get
from ..repository.projects_uow import ProjectsUnitOfWork
from ..services.websocket_manager import ws_manager
from ..utils import validate_message
from ..models.request.request_model import (ProjectCreatedSchema,
                                            CreateProjectSchema,
                                            GetProjectSchema,
                                            SubscribeSchema,
                                            GetProjectsSchema,
                                            )

router = APIRouter()
logger = logging.getLogger(__name__)


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
    async with ProjectsUnitOfWork() as uow:
        project_dom: ProjectDOM = await uow.service.create_project(create_project)
        await uow.commit()
    return ProjectCreatedSchema(
        filename=create_project.filename,
        object_prefix=project_dom.object_prefix,
        upload_link=project_dom.pre_signed_url
    )


@router.get("/projects/{object_prefix}", response_model=GetProjectSchema)
async def get_project(object_prefix: uuid.UUID):
    async with ProjectsUnitOfWork() as uow:
        project: ProjectDOM = await uow.service.get_by_object_prefix(object_prefix)
        return GetProjectSchema(
            object_prefix=project.object_prefix,
            state=project.state,
            versions=s3_object_names_to_urls(project.versions)
        )


@router.get("/projects", response_model=GetProjectsSchema)
async def get_projects(skip: int = 0, limit: int = 10):
    async with ProjectsUnitOfWork() as uow:
        projects: List[ProjectDOM] = await uow.service.list_projects(skip=skip, limit=limit)
        return GetProjectsSchema(
            projects=[
                GetProjectSchema(
                    object_prefix=proj.object_prefix,
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
