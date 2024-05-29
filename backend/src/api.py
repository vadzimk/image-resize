import uuid

from fastapi import APIRouter, UploadFile
from starlette import status

from .schemas import ProjectCreate, ProjectBase

router = APIRouter()


@router.get('/', status_code=status.HTTP_200_OK)
def index():
    return {'Hello': 'World'}


@router.post('/projects', response_model=ProjectCreate, status_code=status.HTTP_200_OK)
def create_project(project_base: ProjectBase):
    link_original = "http://example.com"
    res = ProjectCreate(id=uuid.uuid4(), filename=project_base.filename, link=link_original)
    return res

@router.post("/uploadfile")
async def create_upload_file(file: UploadFile):
    return {"filename": file.filename}
