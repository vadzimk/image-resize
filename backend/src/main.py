import logging

from fastapi import FastAPI


from .api import router
from .services.minio import s3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Logger connected")


logger.info(f"Minio: {'connected' if s3.bucket_exists('images') else 'NOT connected'}")


app = FastAPI()
app.include_router(router)


