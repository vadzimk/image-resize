import json
import re
from typing import Generator, Dict, Any, AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient

from src.main import app

from tests.utils import cleanup_project, upload_originals_s3, Subscription


@pytest_asyncio.fixture(loop_scope='session', scope='session')
def test_client():
    yield TestClient(app)


@pytest_asyncio.fixture(loop_scope='session', scope='session')
async def expected_object_prefix() -> str:
    [object_prefix] = await upload_originals_s3(1)
    yield object_prefix
    await cleanup_project(object_prefix)


@pytest_asyncio.fixture(loop_scope='session', scope='session')
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

    def celery_event_generator(versions: VersionIterator) -> Generator[None, Dict[str, Any], None]:
        while len(versions) > 0:
            msg = (yield)  # Expects a dictionary message via `send`
            print("# receive celery event on progress")
            if msg.get("state") == "PROGRESS":
                assert msg.get("progress").get("done") == len(msg.get("versions").keys()) - 1
            else:
                assert msg.get("state") == "SUCCESS"
            # verify all versions are created
            for s3_key in msg.get("versions").values():
                versions.remove(s3_key)

    versions_iter = VersionIterator()
    async with Subscription(expected_object_prefix) as websocket:
        try:
            celery_versions = celery_event_generator(versions_iter)
            next(celery_versions)
            while True:
                response = await websocket.recv()  # receive s3 event on object creation
                message = json.loads(response)
                if message.get("state") is not None:
                    celery_versions.send(message)
        except StopIteration:  # All versions were created
            return versions_iter


@pytest_asyncio.fixture(loop_scope='session', scope='session')
async def httpx_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as async_client:
        yield async_client
