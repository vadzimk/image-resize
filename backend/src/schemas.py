from dataclasses import dataclass
from enum import Enum
from typing import Dict, Annotated, Optional, List

from pydantic import BaseModel, UUID4, Strict


class CreateProjectSchema(BaseModel):
    filename: str


class ProjectCreatedSchema(CreateProjectSchema):
    project_id: Annotated[UUID4, Strict(False)]
    upload_link: str


class TaskState(str, Enum):
    INITIATE = "INITIATE"
    GOTORIGINAL = "GOTORIGINAL"
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


# @dataclass
# class ImageVersions:
#     original: str
#     thumb: str
#     big_thumb: str
#     big_1920: str
#     d2500: str


class GetProjectSchema(BaseModel):
    project_id: Annotated[UUID4, Strict(False)]
    state: TaskState
    versions: Dict[ImageVersion, str]


class GetProjectsSchema(BaseModel):
    projects: List[GetProjectSchema]


@dataclass
class ProgressDetail:
    done: int
    total: int


class ProjectProgressSchema(GetProjectSchema):
    progress: ProgressDetail


class SubscribeSchema(BaseModel):
    subscribe: Annotated[UUID4, Strict(False)]


class UnSubscribeSchema(BaseModel):
    unsubscribe: Annotated[UUID4, Strict(False)]


class OnSubscribeSchema(SubscribeSchema):
    status_code: int
    status: str
    message: Optional[str] = None


class OnUnSubscribeSchema(UnSubscribeSchema):
    status_code: int
    status: str
    message: Optional[str] = None
