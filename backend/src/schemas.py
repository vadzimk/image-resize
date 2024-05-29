import uuid

from pydantic import BaseModel


class ProjectBase(BaseModel):
    filename: str


class ProjectCreate(ProjectBase):
    id: uuid.UUID
    link: str
