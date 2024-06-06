import asyncio
import logging
import os
import tempfile
from asyncio import AbstractEventLoop
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI
from minio import S3Error

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
        with s3.listen_bucket_notification(bucket_name=bucket_name, events=["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]) as events:
            logger.debug("ENTERED LISTEN (1)")
            for event in events:
                for record in event.get("Records", []):
                    logger.info(f'(01) {record["eventName"]}: {record["s3"]["object"]["key"]}')
                asyncio.run_coroutine_threadsafe(publish_event(event), loop=loop)  # publish to ws_manager
    except S3Error as err:
        logger.error(f"S3 Error: {err}")


def listen_create_s3_events_to_upload_versions(loop: AbstractEventLoop):
    def create_versions(object_name_original: str):
        project_id, basename = object_name_original.rsplit("/")
        basename_wo_ext, ext = basename.rsplit(".")
        input_file_name_less = basename_wo_ext.replace("_original", "")
        sizes = {
            "thumb": (150, 120),
            "big_thumb": (700, 700),
            "big_1920": (1920, 1080),
            "d2500": (2500, 2500)
        }
        versions = {"original": object_name_original}

        try:
            response = s3.get_object(bucket_name=bucket_name, object_name=object_name_original)
            # Read data from response.
            with tempfile.NamedTemporaryFile(delete=True) as temp_input_file:
                temp_input_file.write(response.data)
                with tempfile.TemporaryDirectory() as temp_dir:
                    for size_key, size_value in sizes.items():
                        destination_name = f"{input_file_name_less}_{size_key}.{ext}"
                        destination_temp_path = os.path.join(temp_dir, destination_name)
                        resize_with_aspect_ratio(temp_input_file, destination_temp_path,
                                                 size_value)  # must use temporary file
                        object_name = f"{project_id}/{input_file_name_less}_{size_key}.{ext}"
                        s3.fput_object(bucket_name=bucket_name, object_name=object_name, file_path=destination_temp_path)
                        versions[size_key] = object_name
                # will close temp_input_file
        finally:
            response.close()
            response.release_conn()

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
                        create_versions(s3_object_key)
    except S3Error as err:
        logger.error(f"S3 Error: {err}")

