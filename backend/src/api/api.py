import logging
import uuid
from typing import List
from fastapi import APIRouter
from starlette import status
from .dependencies import ProjectServiceDep
from ..models.domain.object_model import ProjectDOM
from ..services.minio import get_presigned_url_get
from ..models.request.request_model import (
    ProjectCreatedSchema,
    CreateProjectSchema,
    GetProjectSchema,
    GetProjectsSchema,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/images", response_model=ProjectCreatedSchema, status_code=status.HTTP_201_CREATED)
async def get_new_image_url(
        create_project: CreateProjectSchema,
        project_service: ProjectServiceDep
):
    """
    Generate a new image upload url
    """
    project_dom: ProjectDOM = await project_service.create_project(create_project)
    return ProjectCreatedSchema(
        filename=create_project.filename,
        object_prefix=project_dom.object_prefix,
        upload_link=project_dom.pre_signed_url
    )


@router.get("/projects/{object_prefix}", response_model=GetProjectSchema)
async def get_project(
        object_prefix: uuid.UUID,
        project_service: ProjectServiceDep
):
    """ get s3 object urls for a single project """
    project: ProjectDOM = await project_service.get_by_object_prefix(object_prefix)
    return GetProjectSchema(
        object_prefix=project.object_prefix,
        state=project.state,
        versions={
            key: get_presigned_url_get(value)
            for key, value in project.versions.items()
        }
    )


@router.get("/projects", response_model=GetProjectsSchema)
async def get_projects(
        project_service: ProjectServiceDep,
        skip: int = 0,
        limit: int = 10,
):
    """ get all projects represented by their s3 urls """
    projects: List[ProjectDOM] = await project_service.list_projects(skip=skip, limit=limit)
    return GetProjectsSchema(
        projects=[
            GetProjectSchema(
                object_prefix=proj.object_prefix,
                state=proj.state,
                versions={
                    key: get_presigned_url_get(value)
                    for key, value in proj.versions.items()
                }
            ) for proj in projects])
