import uuid

import pytest

from ...src.models.request.request_model import TaskState
from ...src.models.data.data_model import Project
from ...src.repository.projects_repository import ProjectsRepository


# @pytest.mark.skip
@pytest.mark.parametrize("inserted_projects", [1], indirect=True)
async def test_can_get_project(mongo_session, inserted_projects):
    projects_repository = ProjectsRepository(mongo_session)
    inserted_project: Project = inserted_projects[0]
    actual_project = await projects_repository.get({"object_prefix": inserted_project.object_prefix})
    print("actual_project", actual_project)
    print("expected_project", inserted_project)
    assert actual_project == inserted_project


# @pytest.mark.skip
async def test_can_insert_project(mongo_session, inserted_projects):
    projects_repository = ProjectsRepository(mongo_session)
    project_to_insert = Project(object_prefix=uuid.uuid4(), pre_signed_url="http://test-url")
    actual_project = await projects_repository.add(project_to_insert)
    assert actual_project == project_to_insert
    await mongo_session.remove(Project, Project.id == project_to_insert.id)


# @pytest.mark.skip
class TestListProjects:
    number_of_projects_to_create = 11

    @pytest.mark.parametrize("inserted_projects", [number_of_projects_to_create], indirect=True)
    async def test_if_nothing_is_specified_returns_ten_first_projects(self, mongo_session, inserted_projects):
        projects_repository = ProjectsRepository(mongo_session)
        projects = await projects_repository.list()
        assert len(projects) == 10

    # @pytest.mark.skip
    @pytest.mark.parametrize("inserted_projects", [number_of_projects_to_create], indirect=True)
    async def test_when_specified_skip_and_specified_limit_then_returns_projects_left_after_skip(self, mongo_session,
                                                                                                 inserted_projects):
        the_limit = 5
        the_skip = 9
        expected_left_after_skip = 2
        projects_repository = ProjectsRepository(mongo_session)
        projects = await projects_repository.list(skip=the_skip, limit=the_limit)
        assert len(projects) == expected_left_after_skip

    # @pytest.mark.skip
    @pytest.mark.parametrize("inserted_projects", [number_of_projects_to_create], indirect=True)
    async def test_when_specified_limit_and_not_specified_skip_then_returns_projects_limited_by_limit(self,
                                                                                                      mongo_session,
                                                                                                      inserted_projects):
        expected_limit = self.number_of_projects_to_create - 1 if self.number_of_projects_to_create < 10 else 5
        projects_repository = ProjectsRepository(mongo_session)
        projects = await projects_repository.list(limit=expected_limit)
        assert len(projects) == expected_limit

    # @pytest.mark.skip
    @pytest.mark.parametrize("inserted_projects", [number_of_projects_to_create], indirect=True)
    async def test_when_specified_skip_and_not_specified_limit_then_returns_projects_left_after_skip_with_default_limit_ten(
            self, mongo_session, inserted_projects):
        the_skip = 8
        expected_left_after_skip = 3
        projects_repository = ProjectsRepository(mongo_session)
        projects = await projects_repository.list(skip=the_skip)
        assert len(projects) == expected_left_after_skip


async def test_can_update_project(mongo_session, inserted_projects):
    inserted_project: Project = inserted_projects[0]
    print("inserted_project", inserted_project)
    projects_repository = ProjectsRepository(mongo_session)
    patch = {"state": TaskState.REVOKED}
    updated_project = await projects_repository.update({"object_prefix": inserted_project.object_prefix},
                                                       patch)
    print("updated_project", updated_project)
    expected_project = inserted_project.model_copy(update=patch)
    assert updated_project == expected_project
