import asyncio
import logging
import traceback
from asyncio import AbstractEventLoop
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Callable, List

from fastapi import FastAPI
from minio import S3Error

from .domain.events import CeleryTaskUpdated, OriginalUploaded
from .schemas import TaskState, ProjectProgressSchema, GetProjectSchema, ImageVersion
from .worker import rabbitmq_channel_connection, queue_name
from .api import router, bus
from .services.minio import s3, bucket_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"Minio: {'connected' if s3.bucket_exists(bucket_name) else 'NOT connected'}")


def listen_create_s3_events_and_update_db_and_start_celery_tasks(loop: AbstractEventLoop):
    try:
        # create file versions when original is uploaded
        with s3.listen_bucket_notification(bucket_name=bucket_name, events=["s3:ObjectCreated:*"]) as events:
            logger.debug("ENTERED listen_create_s3_events_to_upload_versions")
            for event in events:
                for record in event.get("Records", []):
                    s3_object_key = record["s3"]["object"]["key"]
                    logger.debug(f'listen_create_s3_events_to_upload_versions: {record["eventName"]}: {s3_object_key}')
                    if s3_object_key.rsplit(".")[0].endswith("_original"):
                        logger.debug(f"listen_create_s3_events_to_upload_versions: found original {s3_object_key}")
                        original_object_key = s3_object_key
                        bus.handle(
                            OriginalUploaded(
                                message=GetProjectSchema(
                                    project_id=original_object_key.split("/")[0],
                                    state=TaskState.GOTORIGINAL,
                                    versions={ImageVersion.original: original_object_key}
                                ), loop=loop)
                        )
    except S3Error as err:
        logger.error(f"S3 Error: {err}")
    except Exception:
        logger.error(f"Unexpected error:\n{traceback.format_exc()}")
        raise


def listen_celery_task_notifications_queue(loop: AbstractEventLoop):
    """ publishes celery event to websocket manager and
        updates project in database
    """
    logger.debug(f"Entered listen_celery_task_notifications_queue_to_publish")

    def celery_event_callback(ch, method, properties, body):
        try:
            logger.info(f"Entered listen_celery_task_notifications_queue:celery_event_callback:body: {body}")
            message = ProjectProgressSchema.model_validate_json(body)
            logger.info(f"message = {message}")
            bus.handle(CeleryTaskUpdated(message=message, loop=loop))

        except Exception:
            logger.error(f"Rabbitmq callback error:\n{traceback.format_exc()}")
            raise

    with rabbitmq_channel_connection() as (rabbitmq_channel, rabbitmq_connection):
        logger.info(
            f"listen_celery_task_notifications_queue_to_publish: rabbitmq_channel: {rabbitmq_channel is not None}; rabbitmq_connection: {rabbitmq_connection is not None}")
        rabbitmq_channel.basic_consume(queue=queue_name, on_message_callback=celery_event_callback, auto_ack=True)
        rabbitmq_channel.start_consuming()  # starts loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    # before yield: same as @app.on_event('startup')
    loop = asyncio.get_event_loop()
    listeners: List[Callable] = [listen_create_s3_events_and_update_db_and_start_celery_tasks,
                                 listen_celery_task_notifications_queue]
    with ThreadPoolExecutor(max_workers=3) as executor:
        for listener in listeners:
            executor.submit(listener, loop)
        yield
        # after yield: same as @app.on_event('shutdown')
        executor.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)
app.include_router(router)
