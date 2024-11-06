from typing import Annotated, AsyncGenerator
from fastapi import Depends
from src.db.session import engine
from src.services.project_service import ProjectService
from src.unit_of_work.mongo_uow import MongoUnitOfWork


async def get_project_service() -> AsyncGenerator[ProjectService, None]:
    async with engine.session() as session:
        async with MongoUnitOfWork(session) as uow:
            yield ProjectService(uow)


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
