from fastapi.testclient import TestClient
from ..src.main import app

client = TestClient(app)


def test_read_root():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json() == {'Hello': 'World'}


def test_create_new_project():
    res = client.post("/projects", json={"filename": "testing.jpg"})
    assert res.status_code == 200
    assert res.json()["link"] == "http://example.com"
