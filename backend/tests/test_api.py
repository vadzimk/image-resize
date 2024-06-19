import asyncio
import json
import re
from typing import Generator

import pytest
from .utils import (Subscription,
                    upload_originals_s3,
                    cleanup_project
                    )

from ..src.schemas import GetProjectSchema, ImageVersion


class VersionIterator:
    def __init__(self):
        self._versions = ["big_thumb", "thumb", "big_1920", "d2500"]  # original was uploaded using pre-signed url
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


# @pytest.mark.skip
@pytest.mark.timeout(10)  # times out when versions are not removed
class TestPostNewFile:
    versions = VersionIterator()

    async def test_can_receive_ws_events_when_new_versions_created(self, expected_project_id):

        def s3_event_versions_iterator(versions) -> Generator:
            while len(versions) > 0:
                msg = (yield)
                print("# receive s3 event on object creation")
                s3object_key = msg.get('s3').get('object').get('key')
                assert s3object_key.startswith(expected_project_id)
                # verify all versions are created
                if 's3:ObjectCreated' in msg.get('eventName'):
                    versions.remove(s3object_key)

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

        async with Subscription(expected_project_id) as websocket:
            with pytest.raises(StopIteration):  # All versions were created
                s3_versions = s3_event_versions_iterator(self.versions)
                celery_versions = celery_event_iterator(self.versions)
                next(s3_versions)
                next(celery_versions)
                while True:
                    response = await websocket.recv()  # receive s3 event on object creation
                    message = json.loads(response)
                    if message.get('s3') is not None:
                        s3_versions.send(message)
                    if message.get("state") is not None:
                        celery_versions.send(message)


# @pytest.mark.skip
class TestWebsocket:
    """ endpoint websocket('/ws') """
    async def test_can_unsubscribe(self, expected_project_id):
        async with Subscription(expected_project_id) as websocket:
            response = await websocket.recv()  # any message from s3 or celery listener after file upload
            # print("response1", response)
            await websocket.send(json.dumps({"unsubscribe": expected_project_id}))
            max_retries = 3
            retry_delay = 1
            retry_count = 0
            while retry_count < max_retries:
                try:
                    response = await websocket.recv()
                    # print("response2", response)
                    msg = json.loads(response)
                    assert msg.get("status") == "OK"
                    assert msg.get("unsubscribe") == expected_project_id
                except AssertionError as e:
                    retry_count += 1
                    await asyncio.sleep(retry_delay)
                else:
                    print(f"\nNumber of retries {retry_count}")
                    break  # no exceptions in try, assertion passed
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(websocket.recv(), timeout=2)  # no more messages from websocket after unsubscribe


# @pytest.mark.skip
class TestGetProjectsIdReturnsSingleProject:
    """ endpoint get('/projects/<project_id>') """
    @pytest.fixture(scope="session")
    async def res(self, expected_project_id, test_client):
        await asyncio.sleep(1)  # let the db update state  !! do not remove
        res = test_client.get(f"/projects/{expected_project_id}")
        return res

    def test_project_id_in_response(self, res, expected_project_id):
        project_response = GetProjectSchema.model_validate_json(res.text)
        assert str(project_response.project_id) == expected_project_id

    def test_project_id_in_versions_original(self, res, expected_project_id):
        project_response = GetProjectSchema.model_validate_json(res.text)
        response_versions_original = project_response.versions.get(ImageVersion.original)
        assert response_versions_original is not None
        assert response_versions_original.startswith(str(expected_project_id))


# @pytest.mark.skip
class TestGetProjectsReturnsListOfProjects:
    """ endpoint get('/projects') """
    number_of_projects_to_create = 11

    @pytest.fixture(scope="class", autouse=True)
    async def act(self):
        await cleanup_project()  # make sure no previous projects are in db
        assert self.number_of_projects_to_create > 2
        await upload_originals_s3(self.number_of_projects_to_create)
        await asyncio.sleep(1)  # let db update state

    def test_when_nothing_is_specified_then_returns_ten_first_projects(self, test_client):
        res = test_client.get(f"/projects").json()
        projects = res.get("projects")
        assert len(projects) == 10

    def test_when_specified_skip_and_specified_limit_then_returns_projects_left_after_skip(self, test_client):
        the_limit = 5
        the_skip = 9
        expected_left_after_skip = 2
        res = test_client.get(f"/projects", params={"limit": the_limit, "skip": the_skip}).json()
        projects = res.get("projects")
        assert len(projects) == expected_left_after_skip

    def test_when_specified_limit_and_not_specified_skip_then_returns_projects_limited_by_limit(self, test_client):
        expected_limit = self.number_of_projects_to_create - 1 if self.number_of_projects_to_create < 10 else 5
        res = test_client.get(f"/projects", params={"limit": expected_limit}).json()
        projects = res.get("projects")
        assert len(projects) == expected_limit

    def test_when_specified_skip_and_not_specified_limit_then_returns_projects_left_after_skip_with_default_limit_ten(
            self, test_client):
        the_skip = 8
        expected_left_after_skip = 3
        res = test_client.get(f"/projects", params={"skip": the_skip}).json()
        projects = res.get("projects")
        assert len(projects) == expected_left_after_skip
