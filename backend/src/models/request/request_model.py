"""
Pydantic schemas or request model
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Annotated, Optional, List

from bson import ObjectId
from pydantic import BaseModel, UUID4, Strict, PlainSerializer, ConfigDict

from src.utils import compare_dataclasses

UUID_str = Annotated[Annotated[UUID4, Strict(False)], PlainSerializer(lambda x: str(x), return_type=str)]
ObjectId = Annotated[ObjectId, PlainSerializer(lambda x: str(x), return_type=str)]


class CreateProjectSchema(BaseModel):
    filename: str


class ProjectCreatedSchema(CreateProjectSchema):
    object_prefix: UUID_str
    upload_link: str


class TaskState(str, Enum):
    EXPECTING_ORIGINAL = "EXPECTING_ORIGINAL"  # original upload url created
    GOT_ORIGINAL = "GOT_ORIGINAL"
    STARTED = "STARTED"
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


class GetProjectSchema(BaseModel):
    object_prefix: UUID_str
    state: TaskState
    versions: Dict[ImageVersion, str]


class GetProjectsSchema(BaseModel):
    projects: List[GetProjectSchema]


@compare_dataclasses
@dataclass
class ProgressDetail:
    done: int
    total: int


class ProjectProgressSchema(GetProjectSchema):
    progress: ProgressDetail


class ProjectFailureSchema(BaseModel):
    task_id: ObjectId
    state: TaskState
    error: str

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SubscribeAction(str, Enum):
    SUBSCRIBE = "SUBSCRIBE"
    UNSUBSCRIBE = "UNSUBSCRIBE"


class SubscribeSchema(BaseModel):
    action: SubscribeAction
    object_prefix: UUID_str


class OnSubscribeSchema(SubscribeSchema):
    status_code: int
    status: str
    message: Optional[str] = None
