"""
domain object model
"""
import logging
import uuid
from dataclasses import asdict
from typing import Optional, Dict

from ..request_model import TaskState, ProgressDetail, ImageVersion

logger = logging.getLogger(__name__)


class ProjectDOM:
    def __init__(self, *,
                 project_id: uuid.UUID,
                 pre_signed_url: str,
                 state: Optional[TaskState] = None,
                 error: Optional[str] = None,
                 celery_task_id: Optional[str] = None,
                 versions: Optional[Dict[ImageVersion, str]] = None,
                 progress: Optional[ProgressDetail] = None):
        if versions is None:
            versions = {}
        self.project_id = project_id
        self.pre_signed_url = pre_signed_url
        self.state = state
        self.error = error
        self.celery_task_id = celery_task_id
        self.versions = versions
        self.progress = progress

    def dict(self):
        return {
            "project_id": str(self.project_id),
            "pre_signed_url": self.pre_signed_url,
            "state": self.state,
            "versions": self.versions,
            "progress": asdict(self.progress) if isinstance(self.progress, ProgressDetail) else {},
        }
