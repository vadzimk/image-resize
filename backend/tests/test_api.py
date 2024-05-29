from fastapi.testclient import TestClient
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

