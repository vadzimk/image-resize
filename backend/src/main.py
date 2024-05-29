import logging
import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from minio import Minio

from api import router

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

app = FastAPI()
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(f"{__name__}:app", reload=True)
