import pytest
from odmantic import AIOEngine
from odmantic.session import AIOSession

from ..utils import cleanup_project
from ...src.models.data.data_model import Project
from ...src.models.domain.object_model import ProjectDOM
from ...src.models.request.request_model import CreateProjectSchema
from ...src.repository.projects_uow import create_db_client, create_db_engine, ProjectsUnitOfWork


@pytest.fixture()
def mongo_engine() -> AIOEngine:
    mongo_client = create_db_client()
    return create_db_engine(mongo_client)


@pytest.fixture()
async def mongo_session(mongo_engine) -> AIOSession:
    session = mongo_engine.session()
    await session.start()
    yield session
    await session.end()


@pytest.fixture()
async def created_project_doms(request, mongo_session):
    try:
        number_of_projects = request.param
    except AttributeError:
        number_of_projects = 1
    project_doms = []
    await cleanup_project()
    async with ProjectsUnitOfWork() as uow:
        for _ in range(number_of_projects):
            create_project: CreateProjectSchema = CreateProjectSchema(filename="test_file_name.jpeg")
            project_dom: ProjectDOM = await uow.service.create_project(create_project)
            project_doms.append(project_dom)
        await uow.commit()
    yield project_doms
    for p in project_doms:
        await mongo_session.remove(Project, Project.id == p.id)