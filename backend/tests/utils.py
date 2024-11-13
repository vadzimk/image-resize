import asyncio
import json
import os
from typing import Tuple, List, AsyncGenerator

from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport
from minio.deleteobjects import DeleteObject
from starlette.testclient import TestClient
from websockets import connect, WebSocketClientProtocol
import httpx
from PIL import Image

from src.db.session import create_db_client
# from ..src.unit_of_work.mongo_uow import create_db_client
from src.settings import server_settings
from tests.exceptions import FileUploadFailed
from src.main import app
from src.models.request.request_model import ProjectCreatedSchema
from src.services.minio import s3

load_dotenv()
client = TestClient(app)

BASE_URL = '/api'

def get_images_s3_upload_link_and_object_prefix(image_file_path) -> Tuple[str, str]:
    assert os.path.exists(image_file_path)
    filename = os.path.basename(image_file_path)
    res = client.post(f"{BASE_URL}/images", json={"filename": filename})
    print("res======>")
    print(res.json())

    project_response = ProjectCreatedSchema.model_validate_json(res.text)
    assert project_response.upload_link.startswith('http')
    assert project_response.filename == filename
    return project_response.upload_link, str(project_response.object_prefix)


async def trigger_original_file_upload(image_file_path, upload_link):
    await asyncio.sleep(1)  # wait for client to subscribe !! do not remove it
    res = s3_upload_link_put_file(image_file_path, upload_link)
    if res.status_code != 200:
        raise FileUploadFailed(image_file_path)


async def upload_originals_s3(number: int) -> List[str]:
    """ :returns list of project ids of the uploaded files """

    image_file_path = "./tests/photo.jpeg"

    async def upload_one(file_path) -> str:
        upload_link, object_prefix = get_images_s3_upload_link_and_object_prefix(file_path)
        await trigger_original_file_upload(file_path, upload_link)
        return object_prefix

    tasks = [upload_one(image_file_path) for _ in range(number)]
    object_prefixs = await asyncio.gather(*tasks)
    return list(object_prefixs)


def cleanup_s3_objects(objects: List[str]):
    """
    deletes s3 objects form minio storage
    :param objects: list of str of format "e4302caa-dbd7-4743-ba09-241bd48e35f3/photo_original.jpeg"
    """
    errors = s3.remove_objects(server_settings.MINIO_BUCKET_NAME, [DeleteObject(obj) for obj in objects])
    if len(list(errors)) != 0:
        raise AssertionError
    print(f"cleanup_s3_objects: Done. Deleted {len(objects)} objects.")


async def cleanup_mongodb(object_prefix: str | None = None):
    mongo_client = create_db_client()
    session = await mongo_client.start_session()
    projects_database = session.client[server_settings.MONGO_DATABASE_NAME]
    projects_collection = projects_database["projects"]
    print("cleanup_mongodb:object_prefix:", object_prefix)
    if object_prefix is not None:
        await projects_collection.delete_one({"object_prefix": object_prefix})
    else:
        await projects_collection.delete_many({})  # delete all
        assert await projects_collection.count_documents({}) == 0  # all documents deleted
    await session.end_session()


async def cleanup_project(object_prefix: str | None = None):
    all_objects_to_delete = list(
        s3.list_objects(bucket_name=server_settings.MINIO_BUCKET_NAME,
                        prefix=None if object_prefix is None else str(object_prefix),
                        recursive=True))
    cleanup_s3_objects([o.object_name for o in all_objects_to_delete])
    await cleanup_mongodb(object_prefix)


def s3_upload_link_put_file(image_file_path, upload_link):
    with open(image_file_path, 'rb') as file:
        response = httpx.put(upload_link, content=file, headers={'Content-Type': 'application/json'})
    return response


class Subscription:
    """ Subscribes to websocket to listen for events of an object_prefix
    gets the subscription confirmation
    and returns websocket to receive subsequent events
    """

    def __init__(self, object_prefix: str):
        self.object_prefix = object_prefix
        self.websocket = None

    async def __aenter__(self) -> WebSocketClientProtocol:
        self.websocket = await connect("ws://localhost:8000/ws")
        await self.websocket.send(json.dumps({"action": "SUBSCRIBE", "object_prefix": self.object_prefix}))
        res_confirmation = await self.websocket.recv()
        assert json.loads(res_confirmation).get("status") == "OK"
        return self.websocket

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.websocket.close()


def is_image(file_path):
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except (IOError, SyntaxError):
        return False
