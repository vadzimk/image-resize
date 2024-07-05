import json
import re
import uuid
from typing import Generator, List

import pytest
from starlette.testclient import TestClient

from .utils import cleanup_project, upload_originals_s3, Subscription
from ..src.models.data.data_model import Project
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
async def expected_object_prefix() -> str:
    [object_prefix] = await upload_originals_s3(1)
    yield object_prefix
    await cleanup_project(object_prefix)


@pytest.fixture(scope="session")
async def missed_versions(expected_object_prefix):
    class VersionIterator:
        def __init__(self):
            self._versions = ["big_thumb", "thumb", "big_1920",
                              "d2500"]  # original was uploaded using pre-signed url
            self._index = 0

        def remove(self, s3object_key):
            """ removes version that is mentioned in this s3object_key from the self._versions
                pass if not found
            """
            for version in self._versions:
                pattern = fr'_{version}(?=.*(?:[^.]*\.(?!.*\.))|$)'
                if re.search(pattern, s3object_key):
                    print("s3 created", version)
                    self._versions.remove(version)

        def __len__(self):
            return len(self._versions)

        def __iter__(self):
            return iter(self._versions)

        def __next__(self):
            try:
                item = self._versions[self._index]
            except IndexError:
                raise StopIteration()

            self._index += 1
            return item

        def __repr__(self):
            return str(self._versions)

    def celery_event_iterator(versions) -> Generator:
        while len(versions) > 0:
            msg = (yield)
            print("# receive celery event on progress")
            if msg.get("state") == "PROGRESS":
                assert msg.get("progress").get("done") == len(msg.get("versions").keys()) - 1
            else:
                assert msg.get("state") == "SUCCESS"
            # verify all versions are created
            for s3_key in msg.get("versions").values():
                versions.remove(s3_key)

    versions = VersionIterator()
    async with Subscription(expected_object_prefix) as websocket:
        try:
            celery_versions = celery_event_iterator(versions)
            next(celery_versions)
            while True:
                response = await websocket.recv()  # receive s3 event on object creation
                message = json.loads(response)
                if message.get("state") is not None:
                    celery_versions.send(message)
        except StopIteration:  # All versions were created
            return versions


@pytest.fixture()
async def inserted_projects(request, mongo_session):
    try:
        number_of_projects = request.param
    except AttributeError:
        number_of_projects = 1
    projects: List[Project] = []
    await cleanup_project()
    for _ in range(number_of_projects):
        object_prefix = uuid.uuid4()
        project = Project(object_prefix=object_prefix, pre_signed_url="http://test-url")
        await mongo_session.save(project)
        projects.append(project)
    yield projects
    for p in projects:
        await mongo_session.remove(Project, Project.id == p.id)
