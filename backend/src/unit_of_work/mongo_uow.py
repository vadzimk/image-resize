from abc import ABC, abstractmethod
from odmantic.session import AIOSession
from src.repositories.projects_repository import ProjectRepository


class AbstractUnitOfWork(ABC):

    async def __aenter__(self) -> 'AbstractUnitOfWork':
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()

    @abstractmethod
    async def rollback(self):
        raise NotImplementedError()

    async def commit(self):
        """ called by the client code """
        raise NotImplementedError()


class MongoUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session: AIOSession, use_transaction: bool = False):
        """
        Ensures that operations can be committed or rolled back as a single unit
        @param session: odmantic session
        @param use_transaction: if True all subsequent operations in sessions will be part of transaction
        """
        self._session = session
        self._transaction = None
        self._projectRepository = None
        self._use_transaction = use_transaction
        self.is_transaction_started = False

    async def __aenter__(self) -> 'MongoUnitOfWork':
        if self._use_transaction:
            self._transaction = self._session.transaction()
            await self._transaction.start()
            self.is_transaction_started = True
        self._projectRepository = ProjectRepository(self._session)
        return self

    async def __aexit__(self, *args):
        await super().__aexit__(*args)

    async def commit(self):
        if self._transaction:
            await self._transaction.commit()
            self.is_transaction_started = False

    async def rollback(self):
        if self._transaction:
            await self._transaction.abort()
            self.is_transaction_started = False

    def get_project_repository(self) -> ProjectRepository:
        return self._projectRepository
