import json
import logging
import traceback
import uuid

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from starlette import status
from starlette.websockets import WebSocket, WebSocketDisconnect

from .repository.uow import UnitOfWork
from .repository.projects_repository import ProjectsRepository
from .services.projects_service import ProjectsService
from .exceptions import AlreadySubscribed, NotInSubscriptions
from .websocket_manager import ws_manager
from .schemas import (ProjectCreatedSchema,
                      CreateProjectSchema,
                      GetProjectSchema,
                      SubscribeSchema,
                      UnSubscribeSchema,
                      OnSubscribeSchema,
                      OnUnSubscribeSchema, GetProjectsSchema,
                      )

from .utils import validate_message

router = APIRouter()
logger = logging.getLogger(__name__)


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


@router.get("/projects/{project_id}", response_model=GetProjectSchema, status_code=status.HTTP_200_OK)
async def get_project(project_id: uuid.UUID):
    async with UnitOfWork() as uow:
        repository = ProjectsRepository(uow.session)
        projects_service = ProjectsService(repository)
        project = await projects_service.get_project(project_id)
        return GetProjectSchema(project_id=project.project_id, state=project.state, versions=project.versions)


@router.get("/projects")
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
                    versions=proj.versions
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
            await handle_message(websocket, message)
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception:
        logger.error(f"websocket_endpoint: error:\n{traceback.format_exc()}")
    finally:
        ws_manager.disconnect(websocket)


async def handle_message(websocket: WebSocket, message: dict):
    """
    validates websocket incoming messages and passes them to ws_manager
    """
    logger.debug("Enter handle_message")
    message_model = validate_message(message, [SubscribeSchema, UnSubscribeSchema])
    logger.debug(f"handle_message message_model {message_model}")
    response_message = message_model.model_dump()
    response_message.update({"status_code": 200, "status": "OK"})
    try:
        if isinstance(message_model, SubscribeSchema):
            logger.debug(f"isinstance(message_model, SubscribeSchema) {type(message_model.subscribe)}")
            ws_manager.subscribe(websocket, str(message_model.subscribe))
            logger.debug(f"Subscribed")
        elif isinstance(message_model, UnSubscribeSchema):
            logger.debug(f"isinstance(message_model, UnSubscribeSchema)")
            ws_manager.unsubscribe(websocket, str(message_model.unsubscribe))
        else:
            raise Exception(f"handle_message: unexpected Pydantic Model {type(message_model).__name__}")
    except (AlreadySubscribed, NotInSubscriptions) as err:
        response_message.update({"status_code": 400, "status": "Error", "message": str(err)})
    except Exception as err:
        response_message.update({"status_code": 400, "status": "Error", "message": "Unknown Server Error"})
        raise err
    finally:
        await websocket.send_json(
            jsonable_encoder(
                validate_message(response_message, [OnSubscribeSchema, OnUnSubscribeSchema])
            ))
