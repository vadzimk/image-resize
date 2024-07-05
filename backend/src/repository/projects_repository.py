import logging
import traceback

from typing import List, Tuple, Any, Dict, Optional

from odmantic.session import AIOSession

from .abstract_repository import AbstractRepository
from ..models.data.data_model import Project
from ..exceptions import ProjectNotFoundError

logger = logging.getLogger(__name__)


class ProjectsRepository(AbstractRepository):
    def __init__(self, session: AIOSession):
        self.session = session

    async def list(self,
                   skip: Optional[int] = 0,
                   limit: Optional[int] = None,
                   sort: Optional[List[Tuple[str, Any]]] = None,
                   filters: Optional[Dict[str, Any]] = None) -> List[Project]:
        limit = limit if limit is not None else 10
        filters = filters if filters is not None else {}
        documents = await self.session.find(Project, filters, sort=sort, skip=skip, limit=limit)
        return documents

    async def add(self, project: Project) -> Project:
        project = await self.session.save(project)
        return project

    async def update(self, filters:Dict[str, Any], update: Dict) -> Project:
        project: Project | None = await self.session.find_one(Project, filters)
        if project is None:
            logger.error(f"Unexpected error:\n{traceback.format_exc()}")
            raise ProjectNotFoundError(object_prefix=filters.get("object_prefix"))
        project.model_update(patch_object=update)
        await self.session.save(project)
        logger.debug(f"ProjectsRepository:update: {project}")
        return project

    async def get(self, filters: Dict[str, Any]) -> Project:
        logger.debug(f"ProjectsRepository:get {filters}")

        project: Project | None = await self.session.find_one(Project, filters)
        if project is None:
            raise ProjectNotFoundError()
        logger.debug(f"ProjectsRepository.get:document: {project}")
        return project
