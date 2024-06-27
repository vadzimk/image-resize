from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

from ..settings import server_settings

load_dotenv()


class UnitOfWork:
    def __init__(self):
        self.mongo_client = AsyncIOMotorClient(server_settings.MONGO_DETAILS)
        self.session = None

    async def __aenter__(self) -> 'UnitOfWork':
        self.session = await self.mongo_client.start_session()
        self.transaction = self.session.start_transaction()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        await self.session.end_session()

    async def rollback(self):
        await self.session.abort_transaction()

    async def commit(self):
        """ called by the client code """
        await self.session.commit_transaction()
