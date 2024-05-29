import logging
import os
import uuid
from uuid import UUID

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from minio import Minio
from pydantic import BaseModel
from starlette import status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Logger connected")
load_dotenv()

MINIO_HOSTNAME = "localhost:9000"

client = Minio(
    MINIO_HOSTNAME,
    secure=False,
    access_key=os.getenv("MINIO_ROOT_USER"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD")
)

logger.info(f"Minio: {'connected' if isinstance(client.list_buckets(), list) else 'NOT connected'}")


class ProjectBase(BaseModel):
    id: UUID
    filename: str
    link: str


app = FastAPI()


@app.get('/', status_code=status.HTTP_200_OK)
def index():
    return {'Hello': 'World'}


@app.post('/projects/{id}', response_model=ProjectBase)
def create_project(filename: str):
    link_original = ""
    res = ProjectBase(id=uuid.uuid4(), filename=filename, link=link_original)
    return res


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
