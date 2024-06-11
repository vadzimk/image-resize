from enum import Enum
from typing import Dict, Annotated

from pydantic import BaseModel, UUID4, Strict


class ProjectBase(BaseModel):
    filename: str


class ProjectCreate(ProjectBase):
    project_id: Annotated[UUID4, Strict(False)]
    upload_link: str


class TaskState(str, Enum):
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    REVOKED = "REVOKED"


class Project(BaseModel):
    project_id: Annotated[UUID4, Strict(False)]
    state: TaskState
    versions: Dict[str, str]


class SubscribeModel(BaseModel):
    subscribe: Annotated[UUID4, Strict(False)]


class UnSubscribeModel(BaseModel):
    unsubscribe: Annotated[UUID4, Strict(False)]