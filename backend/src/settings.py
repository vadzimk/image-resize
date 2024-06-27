import os
from pathlib import Path

from pydantic.v1 import BaseSettings

print(Path(os.getcwd()))


class ServerSettings(BaseSettings):
    class Config:
        env_file = Path(os.getcwd()) / ".env"

    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    MINIO_HOSTNAME:str
    MINIO_BUCKET_NAME: str

    MONGO_INITDB_ROOT_USERNAME: str
    MONGO_INITDB_ROOT_PASSWORD: str
    MONGO_DETAILS: str
    MONGO_DATABASE_NAME: str
    MONGO_COLLECTION_NAME: str

    ME_CONFIG_MONGODB_ADMINUSERNAME: str
    ME_CONFIG_MONGODB_ADMINPASSWORD: str
    ME_CONFIG_MONGODB_URL: str


server_settings = ServerSettings()
