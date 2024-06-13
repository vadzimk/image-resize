import asyncio
import json
import os
from typing import Tuple, List
from minio.deleteobjects import DeleteObject
from starlette.testclient import TestClient
from websockets import connect
import httpx

from ..src.main import app
from ..src.schemas import ProjectCreatedSchema
from ..src.services.minio import s3, bucket_name

client = TestClient(app)


def upload_file(image_file_path):
    assert os.path.exists(image_file_path)
    with open(image_file_path, "rb") as image_file:
        files = {"file": (os.path.basename(image_file_path), image_file, "image/jpeg")}
        return client.post("/uploadfile", files=files)


def get_images_s3_upload_link_and_project_id(image_file_path) -> Tuple[str, str]:
    assert os.path.exists(image_file_path)
    filename = os.path.basename(image_file_path)
    res = client.post("/images", json={"filename": filename})
    project_response = ProjectCreatedSchema.model_validate_json(res.text)
    assert project_response.upload_link.startswith('http')
    assert project_response.filename == filename
    return project_response.upload_link, str(project_response.project_id)


def cleanup_s3_objects(objects: List[str]):
    """
    deletes s3 objects form minio storage
    :param objects: list of str of format "e4302caa-dbd7-4743-ba09-241bd48e35f3/photo_original.jpeg"
    """
    errors = s3.remove_objects(bucket_name, [DeleteObject(obj) for obj in objects])
    if len(list(errors)) != 0:
        raise AssertionError
    print(f"cleanup_s3_objects: Done. Deleted {len(objects)} objects.")


def cleanup_project(project_id):
    all_objects_in_project = list(
        s3.list_objects(bucket_name=bucket_name, prefix=str(project_id), recursive=True))
    cleanup_s3_objects([o.object_name for o in all_objects_in_project])


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
        await self.websocket.send(json.dumps({"subscribe": self.project_id}))
        res_confirmation = await self.websocket.recv()
        assert json.loads(res_confirmation).get("status") == "OK"
        return self.websocket

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.websocket.close()


async def trigger_original_file_upload(image_file_path, upload_link):
    await asyncio.sleep(1)  # wait for client to subscribe
    res = s3_upload_link_put_file(image_file_path, upload_link)
    assert res.status_code == 200
