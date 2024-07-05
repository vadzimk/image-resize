import copy
from pprint import pprint

import pytest
import validators

from ...src.models.domain.object_model import ProjectDOM
from ...src.models.data.data_model import Project
from ...src.models.request.request_model import TaskState
from ...src.repository.projects_uow import ProjectsUnitOfWork


# @pytest.mark.skip
async def test_uow_can_create_project(mongo_session, created_project_doms):
    [created_project_dom] = created_project_doms

    print("project_dom")
    pprint(created_project_dom.dict())
    assert created_project_dom.state == TaskState.EXPECTING_ORIGINAL
    assert validators.url(created_project_dom.pre_signed_url, simple_host=True, may_have_port=True)
    actual = await mongo_session.find_one(Project, Project.id == created_project_dom.id)
    assert actual is not None


async def test_can_get_project(created_project_doms):
    created_project_dom: ProjectDOM = created_project_doms[0]
    async with ProjectsUnitOfWork() as uow:
        project_dom = await uow.service.get_by_object_prefix(created_project_dom.object_prefix)
        assert project_dom is not None
        assert project_dom.id == created_project_dom.id


# @pytest.mark.skip
class TestListProjects:
    number_of_projects_to_create = 11

    # @pytest.mark.skip
    @pytest.mark.parametrize("created_project_doms", [number_of_projects_to_create], indirect=True)
    async def test_if_nothing_is_specified_returns_ten_first_projects(self, created_project_doms):
        async with ProjectsUnitOfWork() as uow:
            project_doms = await uow.service.list_projects()
        assert len(project_doms) == 10

    # @pytest.mark.skip
    @pytest.mark.parametrize("created_project_doms", [number_of_projects_to_create], indirect=True)
    async def test_when_specified_skip_and_specified_limit_then_returns_projects_left_after_skip(self,
                                                                                                 created_project_doms):
        the_limit = 5
        the_skip = 9
        expected_left_after_skip = 2
        async with ProjectsUnitOfWork() as uow:
            project_doms = await uow.service.list_projects(skip=the_skip, limit=the_limit)
        assert len(project_doms) == expected_left_after_skip

    @pytest.mark.parametrize("created_project_doms", [number_of_projects_to_create], indirect=True)
    async def test_when_specified_limit_and_not_specified_skip_then_returns_projects_limited_by_limit(self,
                                                                                                      created_project_doms):
        expected_limit = self.number_of_projects_to_create - 1 if self.number_of_projects_to_create < 10 else 5
        async with ProjectsUnitOfWork() as uow:
            project_doms = await uow.service.list_projects(limit=expected_limit)
        assert len(project_doms) == expected_limit

    @pytest.mark.parametrize("created_project_doms", [number_of_projects_to_create], indirect=True)
    async def test_when_specified_skip_and_not_specified_limit_then_returns_projects_left_after_skip_with_default_limit_ten(
            self, created_project_doms):
        the_skip = 8
        expected_left_after_skip = 3
        async with ProjectsUnitOfWork() as uow:
            project_doms = await uow.service.list_projects(skip=the_skip)
        assert len(project_doms) == expected_left_after_skip


async def test_can_update_project(created_project_doms):
    created_project_dom: ProjectDOM = created_project_doms[0]
    patch = {"state": TaskState.REVOKED}
    async with ProjectsUnitOfWork() as uow:
        updated_project_dom = await uow.service.update_by_object_prefix(created_project_dom.object_prefix, patch)
    expected_project_dom = copy.copy(created_project_dom)
    expected_project_dom.state = patch["state"]
    print()
    print("updated_project_dom", updated_project_dom)
    print("expected_project_dom", expected_project_dom)
    assert updated_project_dom == expected_project_dom
