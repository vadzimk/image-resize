import json
import re
import uuid
from typing import Generator, List

import pytest
from starlette.testclient import TestClient

from .utils import cleanup_project, upload_originals_s3, Subscription
from ..src.models.data.data_model import Project
from ..src.main import app




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


