import os

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine
from odmantic.session import AIOSession

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



