import asyncio
import json
import os.path
import tempfile
from pprint import pprint
from typing import Collection

import httpx
import pytest
import validators
from httpx import Response
from starlette.testclient import TestClient

from tests.utils import is_image, cleanup_project, upload_originals_s3, Subscription
from ...src.models.request.request_model import ProjectCreatedSchema, GetProjectSchema, ImageVersion


# @pytest.mark.only
def test_get_new_image_url_returns_upload_link(test_client):
    """ endpoint post('/images') """
    image_file_path = "./tests/photo.jpeg"
    filename = os.path.basename(image_file_path)
    res = test_client.post("/images", json={"filename": filename})
    project_created = ProjectCreatedSchema.model_validate_json(res.text)
    assert validators.url(project_created.upload_link, simple_host=True, may_have_port=True)


# @pytest.mark.only
@pytest.mark.timeout(10)  # times out when versions are not removed
class TestUploadOriginal:
    async def test_all_versions_are_created(self, missed_versions: Collection):
        assert len(missed_versions) == 0


# @pytest.mark.skip
class TestGetProject:
    """ endpoint get('/projects/<object_prefix>') """

    @pytest.fixture(scope="session")
    async def get_project_response(self, expected_object_prefix: str, test_client: TestClient,
                                   missed_versions) -> Response:
        # await asyncio.sleep(3)  # let the db update state -- uses missed_versions fixture instead
        res = test_client.get(f"/projects/{expected_object_prefix}")
        return res

    @pytest.mark.only
    def test_returns_single_project_and_object_prefix_in_response(self, get_project_response: Response,
                                                                  expected_object_prefix: str):
        project_response = GetProjectSchema.model_validate_json(get_project_response.text)
        assert str(project_response.object_prefix) == expected_object_prefix

    # @pytest.mark.skip
    def test_object_prefix_in_versions_original(self, get_project_response: Response, expected_object_prefix: str):
        project_response = GetProjectSchema.model_validate_json(get_project_response.text)
        print("project_response")
        pprint(project_response)
        response_versions_original = project_response.versions.get(ImageVersion.original)
        assert response_versions_original is not None
        assert expected_object_prefix in response_versions_original

    # @pytest.mark.skip
    async def test_can_download_versions_using_versions_urls_and_each_downloaded_file_is_a_valid_image(self,
                                                                                                       get_project_response: Response):
        async def url_saves_to_image(working_dir, url) -> bool:
            """
            download image from url save it in parent_dir and
            return true if it is a valid image
            """
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                filename = response.headers.get("Content-Disposition", "").split("filename=")[-1].strip('"')
                file_path = os.path.join(working_dir, filename)
                with open(file_path, "wb") as file:
                    file.write(response.content)
                return is_image(file_path)

        project = get_project_response.json()
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks = [url_saves_to_image(temp_dir, s3_image_url) for s3_image_url in project.get("versions").values()]
            results = await asyncio.gather(*tasks)
            assert all(results)  # all files are image files


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
        yield

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


# @pytest.mark.skip
@pytest.mark.timeout(10)
class TestWebsocket:
    """ endpoint websocket('/ws') """

    async def test_can_unsubscribe(self, expected_object_prefix):
        async with Subscription(expected_object_prefix) as websocket:
            await websocket.send(json.dumps({"action": "UNSUBSCRIBE", "object_prefix": expected_object_prefix}))
            max_retries = 3
            retry_delay = 1
            retry_count = 0
            while retry_count < max_retries:
                try:
                    response = await websocket.recv()
                    print("response2", response)
                    msg = json.loads(response)
                    assert msg.get("status") == "OK"
                    assert msg.get("action") == "UNSUBSCRIBE"
                    assert msg.get("object_prefix") == expected_object_prefix
                except AssertionError as e:
                    retry_count += 1
                    print("retry_count", retry_count)
                    await asyncio.sleep(retry_delay)
                else:
                    print(f"\nNumber of retries {retry_count}")
                    break  # no exceptions in try, assertion passed
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(websocket.recv(), timeout=2)  # no more messages from websocket after unsubscribe
