import asyncio
import logging
import os
import tempfile
from asyncio import AbstractEventLoop
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from celery import shared_task
from fastapi import FastAPI
from minio import S3Error

from .worker import create_versions
from .services.resize_service import resize_with_aspect_ratio
from .websocket_manager import ws_manager
from .api import router
from .services.minio import s3, bucket_name

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.info("Logger connected")

logger.info(f"Minio: {'connected' if s3.bucket_exists(bucket_name) else 'NOT connected'}")

executor = ThreadPoolExecutor(max_workers=2)  # for each listener


@asynccontextmanager
async def lifespan(app: FastAPI):
    # before yield: same as @app.on_event('startup')
    loop = asyncio.get_event_loop()
    executor.submit(listen_create_delete_s3_events_to_publish, loop)
    executor.submit(listen_create_s3_events_to_upload_versions, loop)
    yield
    # after yield: same as @app.on_event('shutdown')
    executor.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)
app.include_router(router)


def listen_create_delete_s3_events_to_publish(loop: AbstractEventLoop):
    async def publish_event(message: dict):
        await ws_manager.publish(message)

    try:
        # publish create/delete events to WS manager
        with s3.listen_bucket_notification(bucket_name=bucket_name,
                                           events=["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]) as events:
            logger.debug("ENTERED LISTEN (1)")
            for event in events:
                for record in event.get("Records", []):
                    logger.info(f'(01) {record["eventName"]}: {record["s3"]["object"]["key"]}')
                asyncio.run_coroutine_threadsafe(publish_event(event), loop=loop)  # publish to ws_manager
    except S3Error as err:
        logger.error(f"S3 Error: {err}")


def listen_create_s3_events_to_upload_versions(loop: AbstractEventLoop):
    try:
        # create file versions when original is uploaded
        with s3.listen_bucket_notification(bucket_name=bucket_name, events=["s3:ObjectCreated:*"]) as events:
            logger.debug("ENTERED LISTEN (2)")
            for event in events:
                for record in event.get("Records", []):
                    s3_object_key = record["s3"]["object"]["key"]
                    logger.debug(f'(02) {record["eventName"]}: {s3_object_key}')
                    if s3_object_key.rsplit(".")[0].endswith("_original"):
                        logger.debug(f"+++++ found original {s3_object_key}")
                        task = create_versions.s(object_name_original=s3_object_key).apply_async()
                        logger.info(f"task-id: {task.id}")
    except S3Error as err:
        logger.error(f"S3 Error: {err}")
    except Exception as e:
        logger.error(f"Unexpected error {e}")
        raise e
