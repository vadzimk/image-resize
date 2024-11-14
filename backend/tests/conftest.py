import os

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine
from odmantic.session import AIOSession

from dotenv import load_dotenv
# from minio.deleteobjects import DeleteObject
#
# from src.services.minio import s3
# from src.settings import server_settings


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
    engine = create_db_engine(mongo_client)
    yield engine
    mongo_client.close()


@pytest.fixture
async def mongo_session(mongo_engine) -> AIOSession:
    session = mongo_engine.session()
    await session.start()
    yield session
    await session.end()


# @pytest.fixture
# async def cleanup_s3():
#     yield
#     all_objects_to_delete = list(
#         s3.list_objects(
#             bucket_name=server_settings.MINIO_BUCKET_NAME,
#             recursive=True
#         )
#     )
#     errors = s3.remove_objects(server_settings.MINIO_BUCKET_NAME, [DeleteObject(obj) for obj in all_objects_to_delete])
#     assert len(list(errors)) == 0, "Errors happened while removing objects form s3"
#     print(f"cleanup_s3_objects: Done. Deleted {len(all_objects_to_delete)} objects.")
#
#
# @pytest.fixture
# async def cleanup_mongodb(mongo_engine: AIOEngine):
#     yield
#     projects_database = mongo_engine.client[server_settings.MONGO_DATABASE_NAME]
#     projects_collection = projects_database["projects"]
#     await projects_collection.delete_many({})  # delete all
#     assert await projects_collection.count_documents({}) == 0  # all documents deleted
#
#
# @pytest.fixture
# async def cleanup_projects(cleanup_s3, cleanup_mongodb):
#     yield
#     # dependencies are executed on exit
