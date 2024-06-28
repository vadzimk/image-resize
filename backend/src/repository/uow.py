import abc

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorClientSession

from ..services.projects_service import ProjectsService
from .projects_repository import ProjectsRepository
from ..settings import server_settings


class AbstractUnitOfWork(abc.ABC):
    async def __aenter__(self) -> 'AbstractUnitOfWork':
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()

    async def commit(self):
        """ called by the client code """
        await self._commit()

    @abc.abstractmethod
    async def _commit(self):
        raise NotImplementedError()

    @abc.abstractmethod
    async def rollback(self):
        raise NotImplementedError()


class UnitOfWork(AbstractUnitOfWork):

    def __init__(self):
        self.mongo_client = AsyncIOMotorClient(server_settings.MONGO_URL)
        self.session: AsyncIOMotorClientSession | None = None
        self.projects_repository: ProjectsRepository | None = None
        self.projects_service: ProjectsService | None = None

    async def __aenter__(self) -> AbstractUnitOfWork:
        self.session = await self.mongo_client.start_session()
        self.transaction = self.session.start_transaction()
        self.projects_repository = ProjectsRepository(self.session)
        self.projects_service = ProjectsService(self.projects_repository)
        return await super().__aenter__()

    async def __aexit__(self, *args):
        await super().__aexit__(*args)
        await self.session.end_session()

    async def rollback(self):
        await self.session.abort_transaction()

    async def _commit(self):
        await self.session.commit_transaction()
