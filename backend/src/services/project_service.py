import logging
import uuid
from typing import List, Optional, Tuple, Any, Dict

from .minio import get_presigned_url_put
from ..models.data.data_model import Project
from ..models.request.request_model import CreateProjectSchema, TaskState
from ..repositories.projects_repository import ProjectRepository
from ..models.domain.object_model import ProjectDOM
from ..unit_of_work.mongo_uow import MongoUnitOfWork

logger = logging.getLogger(__name__)


class ProjectService:
    def __init__(self, uow: MongoUnitOfWork):
        self._uow = uow
        self._project_repository: ProjectRepository = self._uow.get_project_repository()

    async def get_by_object_prefix(self, object_prefix: uuid.UUID) -> ProjectDOM:
        project: Project = await self._project_repository.get(filters={"object_prefix": object_prefix})
        return ProjectDOM(**project.model_dump())

    async def create_project(self, create_project: CreateProjectSchema) -> ProjectDOM:
        object_prefix = uuid.uuid4()
        input_file_name_less, ext = create_project.filename.rsplit('.', 1)
        object_name_original = f"{str(object_prefix)}/{input_file_name_less}_original.{ext}"
        pre_signed_url = get_presigned_url_put(object_name_original)
        project = Project(state=TaskState.EXPECTING_ORIGINAL,
                          object_prefix=object_prefix,
                          pre_signed_url=pre_signed_url)
        project: Project = await self._project_repository.add(project)
        await self._uow.commit()
        logger.debug(f"projectService:project {project}")
        return ProjectDOM(**project.model_dump())

    async def update_by_object_prefix(self, object_prefix: uuid.UUID, update: dict) -> ProjectDOM:
        logger.debug(f"update_by_object_prefix:object_prefix type: {type(object_prefix)}")
        if not isinstance(object_prefix, uuid.UUID):
            raise Exception(f"object_prefix must be type UUID but got {type(object_prefix)}")

        project = await self._project_repository.update(
            filters={"object_prefix": object_prefix}, update=update)
        await self._uow.commit()
        return ProjectDOM(**project.model_dump())

    async def list_projects(self,
                            skip: Optional[int] = 0,
                            limit: Optional[int] = None,
                            sort: Optional[List[Tuple[str, Any]]] = None,
                            filters: Optional[Dict[str, Any]] = None) -> List[ProjectDOM]:
        projects: List[Project] = await self._project_repository.list(skip=skip, limit=limit, sort=sort, filters=filters)
        return [ProjectDOM(**p.model_dump()) for p in projects]
