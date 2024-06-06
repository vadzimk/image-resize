import json
import logging
import os.path
import shutil
import tempfile
import uuid

from fastapi import APIRouter, UploadFile, HTTPException
from starlette import status
from starlette.websockets import WebSocket, WebSocketDisconnect

from .exceptions import AlreadySubscribed, NotInSubscriptions
from .websocket_manager import ws_manager
from .schemas import (ProjectCreate,
                      ProjectBase,
                      Project)
from .services.minio import s3, get_presigned_url_put, bucket_name
from .services.resize_service import resize_with_aspect_ratio
from .utils import timethis

router = APIRouter()
logger = logging.getLogger(__name__)


# TODO start background processing and return progress
# save file.filename into the s3 storage
# start background task for image processing
# notify about task progress
# https://docs.celeryq.dev/en/stable/userguide/signals.html#task-success
# just register celery signal to call websocket
@router.post("/uploadfile", response_model=Project, status_code=status.HTTP_201_CREATED)
@timethis
def create_upload_file(file: UploadFile):
    project_id = str(uuid.uuid4())
    input_file_name_less, ext = file.filename.rsplit('.', 1)
    with tempfile.NamedTemporaryFile(delete=True) as temp_input_file:
        object_name_original = f"{project_id}/{input_file_name_less}_original.{ext}"

        # need to make a copy because this is not working
        # s3.put_object("images", object_name=object_name_original, data=file.file, length=file.size)
        shutil.copyfileobj(file.file, temp_input_file.file)
        s3.fput_object(bucket_name=bucket_name, object_name=object_name_original, file_path=temp_input_file.name)

        sizes = {
            "thumb": (150, 120),
            "big_thumb": (700, 700),
            "big_1920": (1920, 1080),
            "d2500": (2500, 2500)
        }
        versions = {"original": object_name_original}
        with tempfile.TemporaryDirectory() as temp_dir:
            for size_key, size_value in sizes.items():
                destination_name = f"{input_file_name_less}_{size_key}.{ext}"
                destination_temp_path = os.path.join(temp_dir, destination_name)
                resize_with_aspect_ratio(temp_input_file, destination_temp_path, size_value)  # must use temporary file
                object_name = f"{project_id}/{input_file_name_less}_{size_key}.{ext}"
                s3.fput_object(bucket_name=bucket_name, object_name=object_name, file_path=destination_temp_path)
                versions[size_key] = object_name
        # will close temp_input_file

        return {
            "project_id": project_id,
            "state": "init",
            "versions": versions
        }


@router.post("/images", response_model=ProjectCreate)
def get_new_image_url(project_base: ProjectBase):
    project_id = uuid.uuid4()
    input_file_name_less, ext = project_base.filename.rsplit('.', 1)
    object_name_original = f"{str(project_id)}/{input_file_name_less}_original.{ext}"
    url = get_presigned_url_put(object_name_original)
    return ProjectCreate(
        filename=project_base.filename,
        project_id=project_id,
        upload_link=url
    )


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    logger.info("WS Client connected")
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Path/ws Client message {data}")
            message: dict = json.loads(data)  # TODO add schema validation
            await handle_message(websocket, message)
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        ws_manager.disconnect(websocket)


async def handle_message(websocket: WebSocket, message: dict):
    response_message = message.copy()
    response_message.update({"status_code": "200", "status": "OK"})
    try:
        if "subscribe" in message:
            ws_manager.subscribe(websocket, message["subscribe"])
        elif "unsubscribe" in message:
            ws_manager.unsubscribe(websocket, message["unsubscribe"])
    except (AlreadySubscribed, NotInSubscriptions) as err:
        response_message.update({"status_code": "400", "status": "Error", "message": str(err)})
    except Exception as err:
        response_message.update({"status_code": "400", "status": "Error", "message": "Unknown Server Error"})
        raise err
    finally:
        await websocket.send_json(response_message)

