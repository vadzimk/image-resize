"""
domain object model
"""
import uuid
from dataclasses import asdict
from typing import Optional, Dict

from ..schemas import TaskState, ProgressDetail, ImageVersion


class ProjectDOM:
    def __init__(self, *,
                 project_id: uuid.UUID,
                 pre_signed_url: str,
                 state: Optional[TaskState] = None,
                 versions: Optional[Dict[ImageVersion, str]] = None,
                 progress: Optional[ProgressDetail] = None):
        if versions is None:
            versions = {}
        self.project_id = project_id
        self.pre_signed_url = pre_signed_url
        self.state = state
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
