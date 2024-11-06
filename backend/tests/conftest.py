import os
import uuid
from typing import List, AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine
from odmantic.session import AIOSession
from starlette.testclient import TestClient

# from src.db.session import create_db_client, create_db_engine
from src.main import app

from tests.api.utils import cleanup_project
from src.models.data.data_model import Project

from dotenv import load_dotenv


@pytest_asyncio.fixture(loop_scope='session', scope='session', autouse=True)
def load_env():
    load_dotenv()


@pytest.fixture
def mongo_engine() -> AIOEngine:
    def create_db_client() -> AsyncIOMotorClient:
        """Initialize and return a MongoDB client instance."""
        return AsyncIOMotorClient(
            host=os.getenv('MONGO_URL'),
            username=os.getenv('MONGO_APP_USERNAME'),
            password=os.getenv('MONGO_APP_PASSWORD'),
            authSource=os.getenv('MONGO_DATABASE_NAME'),
            replicaSet=os.getenv('MONGO_REPLICA_SET_NAME'),
            uuidRepresentation="standard"
        )

    def create_db_engine(mongo_client: AsyncIOMotorClient) -> AIOEngine:
        """Create an AIOEngine instance using the given MongoDB client."""
        engine = AIOEngine(
            client=mongo_client,
            database=os.getenv('MONGO_DATABASE_NAME')
        )
        return engine

    mongo_client = create_db_client()
    return create_db_engine(mongo_client)


@pytest.fixture
async def mongo_session(mongo_engine) -> AIOSession:
    session = mongo_engine.session()
    await session.start()
    yield session
    await session.end()


@pytest_asyncio.fixture(loop_scope='function', scope='function')
async def test_client():
    yield TestClient(app)


@pytest_asyncio.fixture(loop_scope='function', scope='function')
async def httpx_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as async_client:
        yield async_client


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
