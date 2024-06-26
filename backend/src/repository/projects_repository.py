import logging
import os
import uuid
from abc import ABC, abstractmethod
from typing import List, Tuple, Any, Dict, Optional

from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorClientSession
from pymongo import ReturnDocument
from dotenv import load_dotenv

from ..exceptions import ProjectNotFoundError
from ..domain.model import ProjectDOM

load_dotenv()

logger = logging.getLogger(__name__)


class ProjectsRepositoryInterface(ABC):
    @abstractmethod
    async def add(self, project: ProjectDOM) -> dict:
        raise NotImplementedError()

    @abstractmethod
    async def get(self, project_id) -> dict:
        raise NotImplementedError()

    @abstractmethod
    async def update(self, project_id: str, update: dict) -> dict:
        raise NotImplementedError()

    @abstractmethod
    async def list(self,
                   skip: Optional[int] = 0,
                   limit: Optional[int] = None,
                   sort: Optional[List[Tuple[str, Any]]] = None,
                   filters: Optional[Dict[str, Any]] = None) -> List[dict]:
        raise NotImplementedError()


class ProjectsRepository(ProjectsRepositoryInterface):
    def __init__(self, session: AsyncIOMotorClientSession):
        self.session = session
        self.projects_database = self.session.client[
            os.getenv("MONGO_DATABASE_NAME", "projects_database")]
        self.projects_collection = self.projects_database[
            os.getenv("MONGO_COLLECTION_NAME", "projects")]  # creates if not exist

    async def list(self,
                   skip: Optional[int] = 0,
                   limit: Optional[int] = None,
                   sort: Optional[List[Tuple[str, Any]]] = None,
                   filters: Optional[Dict[str, Any]] = None) -> List[dict]:
        limit = limit if limit is not None else 10
        filters = filters if filters is not None else {}
        cursor = self.projects_collection.find(filters)
        if sort:
            cursor = cursor.sort(sort)
        documents = await cursor.skip(skip).limit(limit).to_list(limit)
        return [(doc.pop("_id") and doc) for doc in documents]

    async def add(self, project: ProjectDOM) -> dict:
        insert_result = await self.projects_collection.insert_one(project.dict())
        document = await self.projects_collection.find_one({"_id": insert_result.inserted_id})
        return document

    async def update(self, project_id: str, update: dict) -> dict:
        document: dict = await self.projects_collection.find_one_and_update(
            filter={"project_id": str(project_id)},
            update={"$set": jsonable_encoder(update)},
            return_document=ReturnDocument.AFTER
        )
        logger.debug(f"ProjectsRepository:update: {document}")
        if document is None:
            raise ProjectNotFoundError(project_id)
        document.pop("_id")
        return document

    async def get(self, project_id: uuid.UUID) -> dict:
        document: dict | None = await self.projects_collection.find_one({"project_id": str(project_id)})
        if document is None:
            raise ProjectNotFoundError(project_id)
        document.pop("_id")
        logger.debug(f"ProjectsRepository.get:document: {document}")
        return document
