import asyncio
import json
import logging
import traceback
import uuid
from typing import List

from fastapi import APIRouter
from starlette import status
from starlette.websockets import WebSocket, WebSocketDisconnect

from .services.message_bus import bus
from .domain.model import ProjectDOM
from .services.handlers import command_handlers
from .domain import commands
from .services.minio import get_presigned_url_get
from .repository.uow import UnitOfWork
from .repository.projects_repository import ProjectsRepository
from .services.projects_service import ProjectsService
from .websocket_manager import ws_manager
from .schemas import (ProjectCreatedSchema,
                      CreateProjectSchema,
                      GetProjectSchema,
                      SubscribeSchema,
                      GetProjectsSchema,
                      )

from .utils import validate_message

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
    async with UnitOfWork() as uow:
        repository = ProjectsRepository(uow.session)
        project_service = ProjectsService(repository)
        project_dom: ProjectDOM = await project_service.create_project(create_project)
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
        project: ProjectDOM = await projects_service.get_project(project_id)
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
        projects: List[ProjectDOM] = await project_service.list_projects(skip=skip, limit=limit)
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
