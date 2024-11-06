from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine

from ..settings import server_settings


def create_db_client() -> AsyncIOMotorClient:
    """Initialize and return a MongoDB client instance."""
    mongo_client = AsyncIOMotorClient(host=server_settings.MONGO_URL,
                                      username=server_settings.MONGO_APP_USERNAME,
                                      password=server_settings.MONGO_APP_PASSWORD,
                                      authSource=server_settings.MONGO_DATABASE_NAME,
                                      replicaSet=server_settings.MONGO_REPLICA_SET_NAME,
                                      uuidRepresentation="standard")
    return mongo_client


def create_db_engine(mongo_client: AsyncIOMotorClient) -> AIOEngine:
    """Create an AIOEngine instance using the given MongoDB client."""
    engine = AIOEngine(client=mongo_client, database=server_settings.MONGO_DATABASE_NAME)
    return engine


engine = create_db_engine(create_db_client())

