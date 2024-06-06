import os
from typing import Tuple, List

from fastapi.testclient import TestClient

from ..src.schemas import ProjectCreate
from minio.deleteobjects import DeleteObject
from ..src.services.minio import s3
import httpx
from ..src.main import app

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
    project_response = ProjectCreate.model_validate_json(res.text)
    assert project_response.upload_link.startswith('http')
    assert project_response.filename == filename
    return project_response.upload_link, str(project_response.project_id)


def cleanup_s3_objects(objects: List[str]):
    """
    deletes s3 objects form minio storage
    :param objects: list of str of format "e4302caa-dbd7-4743-ba09-241bd48e35f3/photo_original.jpeg"
    """
    errors = s3.remove_objects("images", [DeleteObject(obj) for obj in objects])
    if len(list(errors)) != 0:
        raise AssertionError
    print(f"cleanup_s3_objects: Done. Deleted {len(objects)} objects.")


def s3_upload_link_put_file(image_file_path, upload_link):
    with open(image_file_path, 'rb') as file:
        response = httpx.put(upload_link, content=file, headers={'Content-Type': 'application/json'})
    return response
