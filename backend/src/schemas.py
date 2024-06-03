import uuid
from typing import Dict

from pydantic import BaseModel


class ProjectBase(BaseModel):  # TODO delete, not used in real endpoints
    filename: str


class ProjectCreate(ProjectBase):  # TODO delete, not used in real endpoints
    project_id: uuid.UUID
    upload_link: str


class Project(BaseModel):
    project_id: uuid.UUID
    state: str  # TODO replace with celery states
    versions: Dict[str, str]

