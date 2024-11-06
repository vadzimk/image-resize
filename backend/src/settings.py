import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

print(Path(os.getcwd()))


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(os.getcwd()) / ".env",
        validate_default=False,  # skip validation of default fields
        extra='ignore'  # ignore extra fields in the .env file
    )

    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    MINIO_HOSTNAME: str
    MINIO_BUCKET_NAME: str

    MONGO_APP_USERNAME: str
    MONGO_APP_PASSWORD: str
    MONGO_URL: str
    MONGO_DATABASE_NAME: str
    MONGO_REPLICA_SET_NAME: str

    task_notifications_queue: str = "task_notifications"  # also called routing_key or channel or event_type or event_name or topic or queue


server_settings = ServerSettings()
