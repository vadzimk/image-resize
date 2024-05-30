import os.path
import shutil
import tempfile
import uuid

from fastapi import APIRouter, UploadFile
from starlette import status

from .schemas import ProjectCreate, ProjectBase, Project
from .services.minio import s3
from .services.resize_service import resize_with_aspect_ratio
from .utils import timethis

router = APIRouter()


@router.get('/', status_code=status.HTTP_200_OK)
def index():
    return {'Hello': 'World'}


@router.post('/projects', response_model=ProjectCreate, status_code=status.HTTP_200_OK)
def create_project(project_base: ProjectBase):
    link_original = "http://example.com"
    res = ProjectCreate(id=uuid.uuid4(), filename=project_base.filename, link=link_original)
    return res


# TODO start background processing and return progress
# save file.filename into the s3 storage
# start background task for image processing
# notify about task progress
# https://docs.celeryq.dev/en/stable/userguide/signals.html#task-success
# just register celery signal to call websocket
@router.post("/uploadfile", response_model=Project, status_code=status.HTTP_201_CREATED)
@timethis
def create_upload_file(file: UploadFile):
    project_id = str(uuid.uuid4())
    input_file_name_less, ext = file.filename.rsplit('.', 1)
    with tempfile.NamedTemporaryFile(delete=True) as temp_input_file:
        object_name_original = f"{project_id}/{input_file_name_less}_original.{ext}"

        # need to make a copy because this is not working
        # s3.put_object("images", object_name=object_name_original, data=file.file, length=file.size)
        shutil.copyfileobj(file.file, temp_input_file.file)
        s3.fput_object("images", object_name=object_name_original, file_path=temp_input_file.name)

        sizes = {
            "thumb": (150, 120),
            "big_thumb": (700, 700),
            "big_1920": (1920, 1080),
            "d2500": (2500, 2500)
        }
        versions = {"original": object_name_original}
        with tempfile.TemporaryDirectory() as temp_dir:
            for size_key, size_value in sizes.items():
                destination_name = f"{input_file_name_less}_{size_key}.{ext}"
                destination_temp_path = os.path.join(temp_dir, destination_name)
                resize_with_aspect_ratio(temp_input_file, destination_temp_path, size_value)  # must use temporary file
                object_name = f"{project_id}/{input_file_name_less}_{size_key}.{ext}"
                s3.fput_object("images", object_name=object_name, file_path=destination_temp_path)
                versions[size_key] = object_name
        # will close temp_input_file

        return {
            "project_id": project_id,
            "state": "init",
            "versions": versions
        }
