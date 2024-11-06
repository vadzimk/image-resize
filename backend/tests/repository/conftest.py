import uuid
from typing import List

import pytest

from src.models.data.data_model import Project
from tests.utils import cleanup_project


@pytest.fixture
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
