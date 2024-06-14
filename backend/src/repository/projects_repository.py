import logging
import uuid
from abc import ABC, abstractmethod
from typing import List

from motor.motor_asyncio import AsyncIOMotorClientSession
from pymongo import ReturnDocument

from ..exceptions import ProjectNotFoundError
from ..schemas import TaskState
from ..services.project_dom import ProjectDOM

logger = logging.getLogger(__name__)


class ProjectsRepositoryInterface(ABC):
    @abstractmethod
    async def add(self, project_id: uuid.UUID, pre_signed_url: str) -> ProjectDOM:
        pass

    @abstractmethod
    async def get(self, project_id) -> ProjectDOM | None:
        pass

    @abstractmethod
    async def update(self, project_id: str, update: dict) -> ProjectDOM:
        pass

    @abstractmethod
    def list(self) -> List[ProjectDOM]:
        pass


class ProjectsRepository(ProjectsRepositoryInterface):
    def __init__(self, session: AsyncIOMotorClientSession):
        self.session = session
        self.projects_database = self.session.client["projects_database"]  # creates if not exist TODO replace by env
        self.projects_collection = self.projects_database["projects"]  # creates if not exist

    def list(self) -> List[ProjectDOM]:
        pass

    async def add(self, project_id: uuid.UUID, pre_signed_url: str) -> ProjectDOM:
        project = ProjectDOM(project_id=project_id,
                             state=TaskState.INITIATE,
                             pre_signed_url=pre_signed_url)
        await self.projects_collection.insert_one(project.dict())
        return project

    async def update(self, project_id: str, update: dict) -> ProjectDOM:
        document = await self.projects_collection.find_one_and_update(
            filter={"project_id": project_id},
            update={"$set": update},
            return_document=ReturnDocument.AFTER
        )
        logger.debug(f"ProjectsRepository:update: {document}")
        if document is None:
            raise ProjectNotFoundError(project_id)
        res = dict(document)
        res.pop("_id")
        return ProjectDOM(**res)

    async def get(self, project_id: uuid.UUID) -> ProjectDOM:
        document: dict | None = await self.projects_collection.find_one({"project_id": str(project_id)})
        if document is None:
            raise ProjectNotFoundError(project_id)
        document.pop("_id")
        logger.debug(f"ProjectsRepository.get:document: {document}")
        return ProjectDOM(**document)

