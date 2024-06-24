import logging
import uuid
from typing import List, Optional, Tuple, Any, Dict

from .minio import get_presigned_url_put
from ..schemas import CreateProjectSchema, TaskState
from ..repository.projects_repository import ProjectsRepositoryInterface
from ..domain.model import ProjectDOM

logger = logging.getLogger(__name__)


class ProjectsService:
    def __init__(self, projects_repository: ProjectsRepositoryInterface):
        self.projects_repository = projects_repository

    async def get_project(self, project_id) -> ProjectDOM:
        document = await self.projects_repository.get(project_id)
        return ProjectDOM(**document)

    async def create_project(self, create_project: CreateProjectSchema) -> ProjectDOM:
        project_id = uuid.uuid4()
        input_file_name_less, ext = create_project.filename.rsplit('.', 1)
        object_name_original = f"{str(project_id)}/{input_file_name_less}_original.{ext}"
        pre_signed_url = get_presigned_url_put(object_name_original)

        project = ProjectDOM(project_id=project_id,
                             state=TaskState.INITIATE,
                             pre_signed_url=pre_signed_url)

        inserted_document = await self.projects_repository.add(project)
        inserted_document.pop("_id")
        return ProjectDOM(**inserted_document)

    async def update_project(self, project_id: str, update: dict) -> ProjectDOM:
        document = await self.projects_repository.update(project_id, update)
        return ProjectDOM(**document)

    async def list_projects(self,
                            skip: Optional[int] = 0,
                            limit: Optional[int] = None,
                            sort: Optional[List[Tuple[str, Any]]] = None,
                            filters: Optional[Dict[str, Any]] = None) -> List[ProjectDOM]:
        documents: List[dict] = await self.projects_repository.list(skip=skip, limit=limit, sort=sort, filters=filters)
        return [ProjectDOM(**doc) for doc in documents]
