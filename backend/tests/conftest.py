import pytest
from starlette.testclient import TestClient

from .utils import cleanup_project, upload_originals_s3
from ..src.main import app


@pytest.fixture(scope="session")
def test_client():
    return TestClient(app)


@pytest.fixture(scope="session", autouse=True)
async def setup_teardown():
    # setup code
    print("\nGoing to setup")
    print("Setup Done")
    yield
    # teardown code
    print("\nGoing to teardwon")
    await cleanup_project()
    print("Teardwon Done")


@pytest.fixture(scope="session")
async def expected_project_id() -> str:
    [project_id] = await upload_originals_s3(1)
    yield project_id
    await cleanup_project(project_id)
