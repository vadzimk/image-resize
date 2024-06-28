import asyncio
import json
import os
from typing import Tuple, List

from dotenv import load_dotenv
from minio.deleteobjects import DeleteObject
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.testclient import TestClient
from websockets import connect
import httpx
from PIL import Image

from ..src.settings import server_settings
from .exceptions import FileUploadFailed
from ..src.main import app
from ..src.models.request.request_model import ProjectCreatedSchema
from ..src.services.minio import s3

load_dotenv()
client = TestClient(app)


def get_images_s3_upload_link_and_project_id(image_file_path) -> Tuple[str, str]:
    assert os.path.exists(image_file_path)
    filename = os.path.basename(image_file_path)
    res = client.post("/images", json={"filename": filename})
    project_response = ProjectCreatedSchema.model_validate_json(res.text)
    assert project_response.upload_link.startswith('http')
    assert project_response.filename == filename
    return project_response.upload_link, str(project_response.project_id)


async def trigger_original_file_upload(image_file_path, upload_link):
    await asyncio.sleep(1)  # wait for client to subscribe !! do not remove it
    res = s3_upload_link_put_file(image_file_path, upload_link)
    if res.status_code != 200:
        raise FileUploadFailed(image_file_path)


async def upload_originals_s3(number: int) -> List[str]:
    """ :returns list of project ids of the uploaded files """

    image_file_path = "./tests/photo.jpeg"

    async def upload_one(file_path) -> str:
        upload_link, project_id = get_images_s3_upload_link_and_project_id(file_path)
        await trigger_original_file_upload(file_path, upload_link)
        return project_id

    tasks = [upload_one(image_file_path) for _ in range(number)]
    project_ids = await asyncio.gather(*tasks)
    return list(project_ids)


def cleanup_s3_objects(objects: List[str]):
    """
    deletes s3 objects form minio storage
    :param objects: list of str of format "e4302caa-dbd7-4743-ba09-241bd48e35f3/photo_original.jpeg"
    """
    errors = s3.remove_objects(server_settings.MINIO_BUCKET_NAME, [DeleteObject(obj) for obj in objects])
    if len(list(errors)) != 0:
        raise AssertionError
    print(f"cleanup_s3_objects: Done. Deleted {len(objects)} objects.")


async def cleanup_mongodb(project_id: str | None = None):
    mongo_client = AsyncIOMotorClient(server_settings.MONGO_URL)
    session = await mongo_client.start_session()
    projects_database = session.client[server_settings.MONGO_DATABASE_NAME]
    projects_collection = projects_database[server_settings.MONGO_COLLECTION_NAME]
    print("cleanup_mongodb:project_id:", project_id)
    if project_id is not None:
        await projects_collection.delete_one({"project_id": project_id})
    else:
        await projects_collection.delete_many({})  # delete all
        assert await projects_collection.count_documents({}) == 0  # all documents deleted
    await session.end_session()


async def cleanup_project(project_id: str | None = None):
    all_objects_to_delete = list(
        s3.list_objects(bucket_name=server_settings.MINIO_BUCKET_NAME,
                        prefix=None if project_id is None else str(project_id),
                        recursive=True))
    cleanup_s3_objects([o.object_name for o in all_objects_to_delete])
    await cleanup_mongodb(project_id)


def s3_upload_link_put_file(image_file_path, upload_link):
    with open(image_file_path, 'rb') as file:
        response = httpx.put(upload_link, content=file, headers={'Content-Type': 'application/json'})
    return response


class Subscription:
    """ Subscribes to websocket to listen to events of a project_id
    gets the subscription confirmation
    and returns websocket to receive subsequent events
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.websocket = None

    async def __aenter__(self):
        self.websocket = await connect("ws://localhost:8000/ws")
        await self.websocket.send(json.dumps({"action": "SUBSCRIBE", "project_id": self.project_id}))
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
