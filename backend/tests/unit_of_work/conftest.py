from src.services.project_service import ProjectService
from typing import AsyncGenerator

import pytest

from src.unit_of_work.mongo_uow import MongoUnitOfWork
from tests.api.utils import cleanup_project
from ...src.models.data.data_model import Project
from ...src.models.domain.object_model import ProjectDOM
from ...src.models.request.request_model import CreateProjectSchema


# @pytest.fixture(scope='session')
# def event_loop(request):
#     loop = asyncio.get_event_loop()
#     yield loop
#     loop.close()


@pytest.fixture
async def project_service(mongo_engine) -> AsyncGenerator[ProjectService, None]:
    # async with get_mongo_session() as session:
    #     async with MongoUnitOfWork(session) as uow:
    #         project_service = ProjectService(uow)
    #         yield project_service
    async with mongo_engine.session() as session:
        async with MongoUnitOfWork(session) as uow:
            yield ProjectService(uow)
    # async for project_srv in get_project_service():
    #     yield project_srv


@pytest.fixture
async def created_project_doms(request, mongo_session, project_service):
    try:
        number_of_projects = request.param
    except AttributeError:
        number_of_projects = 1
    project_doms = []
    await cleanup_project()

    # async with ProjectsUnitOfWork() as uow:
    #     for _ in range(number_of_projects):
    #         create_project: CreateProjectSchema = CreateProjectSchema(filename="test_file_name.jpeg")
    #         project_dom: ProjectDOM = await uow.service.create_project(create_project)
    #         project_doms.append(project_dom)
    #     await uow.commit()

    for _ in range(number_of_projects):
        create_project: CreateProjectSchema = CreateProjectSchema(filename="test_file_name.jpeg")
        project_dom: ProjectDOM = await project_service.create_project(create_project)
        project_doms.append(project_dom)

    yield project_doms
    for p in project_doms:
        await mongo_session.remove(Project, Project.id == p.id)


