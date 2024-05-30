import os
from pprint import pprint

from fastapi.testclient import TestClient
from minio.deleteobjects import DeleteObject

from ..src.services.minio import s3
from ..src.schemas import Project
from ..src.main import app

client = TestClient(app)


def test_read_root():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json() == {'Hello': 'World'}


def test_create_project_returns_upload_link():
    filename = "testing.jpg"
    res = client.post("/projects", json={"filename": filename})
    assert res.status_code == 200
    body = res.json()
    assert body["link"] == "http://example.com"
    assert body["filename"] == filename
    print("type", type(body["id"]))
    assert isinstance(body["id"], str) and len(body["id"]) > 0


def test_upload_file_returns_Project():
    image_file_path = "./tests/photo.jpeg"
    assert os.path.exists(image_file_path)
    with open(image_file_path, "rb") as image_file:
        files = {"file": (os.path.basename(image_file_path), image_file, "image/jpeg")}
        res = client.post("/uploadfile", files=files)
        print("response: ", end='')
        pprint(res.json())
        assert res.status_code == 201
        project_response = Project.model_validate_json(res.text)
        assert project_response.project_id is not None
        objects = project_response.versions.values()
    # cleanup
    errors = s3.remove_objects("images", [DeleteObject(obj) for obj in objects])
    assert len(list(errors)) == 0

