import uuid
from typing import Dict
from odmantic import Model
from pydantic import ConfigDict
from ..request.request_model import TaskState, ImageVersion, ProgressDetail


class Project(Model):
    pre_signed_url: str
    object_prefix: uuid.UUID  # previously, project_id
    state: TaskState | None = None
    error: str | None = None
    celery_task_id: uuid.UUID | None = None
    versions: Dict[ImageVersion, str] | None = None
    progress: ProgressDetail | None = None

    model_config = ConfigDict(
        collection="projects",
        # arbitrary_types_allowed=True,
    )

    def __eq__(self, other):
        if not isinstance(other, Project):
            return False
        return self.model_dump() == other.model_dump()