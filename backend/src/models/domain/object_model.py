"""
domain object model
"""
import logging
import uuid
from dataclasses import asdict
from typing import Optional, Dict

from ..request.request_model import TaskState, ProgressDetail, ImageVersion

logger = logging.getLogger(__name__)


class ProjectDOM: # domain object model
    def __init__(self, *,
                 id: uuid.UUID,
                 pre_signed_url: str,
                 object_prefix: uuid.UUID | None = None,  # previously, project_id
                 state: TaskState | None = None,
                 error: str | None = None,
                 celery_task_id: str | None = None,
                 versions: Dict[ImageVersion, str] | None = None,
                 progress: ProgressDetail | None = None):
        if versions is None:
            versions = {}
        self.id = id
        self.pre_signed_url = pre_signed_url
        self.object_prefix = object_prefix
        self.state = state
        self.error = error
        self.celery_task_id = celery_task_id
        self.versions = versions
        self.progress = progress

    def dict(self):
        return {
            "id": str(self.id),
            "pre_signed_url": self.pre_signed_url,
            "state": self.state,
            "versions": self.versions,
            "progress": asdict(self.progress) if isinstance(self.progress, ProgressDetail) else {},
        }

    def __eq__(self, other):
        if not isinstance(other, ProjectDOM):
            return False
        return all(self.__dict__[key] == other.__dict__[key]
                   for key in self.__dict__)

    def create_versions(self):
        pass
    # TODO move logic to the domain object model?
