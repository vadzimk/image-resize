from dataclasses import dataclass
from enum import Enum
from typing import Dict, Annotated, Optional

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


class ImageVersion(str, Enum):
    original = "original"
    thumb = "thumb"
    big_thumb = "big_thumb"
    big_1920 = "big_1920"
    d2500 = "d2500"


class Project(BaseModel):
    project_id: Annotated[UUID4, Strict(False)]
    state: TaskState
    versions: Dict[ImageVersion, str]


@dataclass
class ProgressDetail:
    done: int
    total: int


class ProjectProgressModel(Project):
    progress: ProgressDetail


class SubscribeModel(BaseModel):
    subscribe: Annotated[UUID4, Strict(False)]


class UnSubscribeModel(BaseModel):
    unsubscribe: Annotated[UUID4, Strict(False)]


class OnSubscribeModel(SubscribeModel):
    status_code: int
    status: str
    message: Optional[str] = None


class OnUnSubscribeModel(UnSubscribeModel):
    status_code: int
    status: str
    message: Optional[str] = None

