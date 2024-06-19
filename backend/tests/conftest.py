import pytest
from starlette.testclient import TestClient

from .utils import cleanup_project
from ..src.main import app


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture(scope="function", autouse=True)
async def setup_teardown():
    # setup code
    print("\nGoing to setup")
    print("Setup Done")
    yield
    # teardown code
    print("\nGoing to teardwon")
    await cleanup_project()
    print("Teardwon Done")
