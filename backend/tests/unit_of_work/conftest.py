from src.services.project_service import ProjectService
from typing import AsyncGenerator

import pytest

from src.unit_of_work.mongo_uow import MongoUnitOfWork
from tests.utils import cleanup_project
from ...src.models.data.data_model import Project
from ...src.models.domain.object_model import ProjectDOM
from ...src.models.request.request_model import CreateProjectSchema


@pytest.fixture
async def project_service(mongo_engine) -> AsyncGenerator[ProjectService, None]:
    async with MongoUnitOfWork() as uow:
        yield ProjectService(uow)



@pytest.fixture
async def created_project_doms(request, mongo_session, project_service):
    try:
        number_of_projects = request.param
    except AttributeError:
        number_of_projects = 1
    project_doms = []
    await cleanup_project()

    for _ in range(number_of_projects):
        create_project: CreateProjectSchema = CreateProjectSchema(filename="test_file_name.jpeg")
        project_dom: ProjectDOM = await project_service.create_project(create_project)
        project_doms.append(project_dom)

    yield project_doms
    for p in project_doms:
        await mongo_session.remove(Project, Project.id == p.id)


