from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine
from odmantic.session import AIOSession

from .abstract_uow import AbstractUnitOfWork
from ..services.projects_service import ProjectsService
from .projects_repository import ProjectsRepository
from ..settings import server_settings


def create_db_client() -> AsyncIOMotorClient:
    mongo_client = AsyncIOMotorClient(host=server_settings.MONGO_URL,
                                      username=server_settings.MONGO_APP_USERNAME,
                                      password=server_settings.MONGO_APP_PASSWORD,
                                      authSource=server_settings.MONGO_DATABASE_NAME,
                                      replicaSet=server_settings.MONGO_REPLICA_SET_NAME,
                                      uuidRepresentation="standard")
    return mongo_client


def create_db_engine(mongo_client: AsyncIOMotorClient) -> AIOEngine:
    engine = AIOEngine(client=mongo_client, database=server_settings.MONGO_DATABASE_NAME)
    return engine


def close_db_connection(mongo_client: AsyncIOMotorClient):
    mongo_client.close()


class ProjectsUnitOfWork(AbstractUnitOfWork):

    def __init__(self):
        super().__init__()
        self.mongo_client = create_db_client()
        self.engine = create_db_engine(self.mongo_client)
        self.session: AIOSession | None = None
        self.repository: ProjectsRepository | None = None
        self.service: ProjectsService | None = None

    async def __aenter__(self) -> 'ProjectsUnitOfWork':
        self.session: AIOSession = self.engine.session()
        await self.session.start()
        self.transaction = self.session.transaction()
        await self.transaction.start()
        self.repository = ProjectsRepository(self.session)
        self.service = ProjectsService(self.repository)
        return await super().__aenter__()

    async def __aexit__(self, *args):
        await super().__aexit__(*args)
        await self.session.end()

    async def rollback(self):
        await self.transaction.abort()

    async def _commit(self):
        await self.transaction.commit()
