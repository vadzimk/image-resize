import abc


class AbstractUnitOfWork(abc.ABC):
    def __init__(self):
        self.service = None

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
