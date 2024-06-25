import asyncio
import json
import logging
import traceback
from asyncio import AbstractEventLoop
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI
from minio import S3Error

from .domain.events import CeleryTaskUpdated
from .exceptions import ProjectNotFoundError
from .schemas import TaskState, ProjectProgressSchema
from .services.projects_service import ProjectsService
from .repository.projects_repository import ProjectsRepository
from .repository.uow import UnitOfWork
from .worker import create_versions, rabbitmq_channel_connection, queue_name
from .websocket_manager import ws_manager
from .api import router, bus
from .services.minio import s3, bucket_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"Minio: {'connected' if s3.bucket_exists(bucket_name) else 'NOT connected'}")
executor = ThreadPoolExecutor(max_workers=3)  # for each listener


@asynccontextmanager
async def lifespan(app: FastAPI):
    # before yield: same as @app.on_event('startup')
    loop = asyncio.get_event_loop()
    executor.submit(listen_create_delete_s3_events_and_publish_to_ws, loop)
    executor.submit(listen_create_s3_events_and_update_db_and_start_celery_tasks, loop)
    executor.submit(listen_celery_task_notifications_queue, loop)
    yield
    # after yield: same as @app.on_event('shutdown')
    executor.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)
app.include_router(router)


async def update_project_in_db(project_id: str, update: dict):
    try:
        async with UnitOfWork() as uow:
            repository = ProjectsRepository(uow.session)
            projects_service = ProjectsService(repository)
            updated = await projects_service.update_project(project_id, update)
            await uow.commit()
            logger.info(f"update_project_in_db: {updated.dict()}")
    except ProjectNotFoundError as e:
        logger.error(e)


# TODO remove this listener no need in publishing to the client websocket connections about file upload events
def listen_create_delete_s3_events_and_publish_to_ws(loop: AbstractEventLoop):
    try:
        # publish create/delete events to WS manager
        with s3.listen_bucket_notification(bucket_name=bucket_name,
                                           events=["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]) as events:
            logger.debug("ENTERED listen_create_delete_s3_events_to_publish")
            for event in events:
                for record in event.get("Records", []):
                    logger.debug(
                        f'listen_create_delete_s3_events_to_publish: {record["eventName"]}: {record["s3"]["object"]["key"]}')
                asyncio.run_coroutine_threadsafe(ws_manager.publish_s3_event(event), loop=loop)  # publish to ws_manager
    except S3Error as err:
        logger.error(f"S3 Error: {err}")


def listen_create_s3_events_and_update_db_and_start_celery_tasks(loop: AbstractEventLoop):
    async def original_update_db(original_object_key: str):
        project_id = original_object_key.split("/")[0]
        update = {
            "state": TaskState.GOTORIGINAL,
            "versions": {
                "original": original_object_key
            }
        }
        await update_project_in_db(project_id, update)

    def on_original_upload(s3_object_key):
        asyncio.run_coroutine_threadsafe(original_update_db(s3_object_key), loop=loop)
        celery_task = create_versions.s(object_name_original=s3_object_key).apply_async()
        result = celery_task.get()
        logger.info(
            f"listen_create_s3_events_to_upload_versions: Celery task created task-id: {celery_task.id}, result: {result}")

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
                        on_original_upload(s3_object_key)

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

            # asyncio.run_coroutine_threadsafe(
            #     ws_manager.publish_celery_event(message),
            #     loop=loop)

            asyncio.run_coroutine_threadsafe(
                update_project_in_db(
                    project_id=message.project_id,
                    update=message.model_dump()),
                loop=loop)
        except Exception:
            logger.error(f"Rabbitmq callback error:\n{traceback.format_exc()}")
            raise

    with rabbitmq_channel_connection() as (rabbitmq_channel, rabbitmq_connection):
        logger.info(
            f"listen_celery_task_notifications_queue_to_publish: rabbitmq_channel: {rabbitmq_channel is not None}; rabbitmq_connection: {rabbitmq_connection is not None}")
        rabbitmq_channel.basic_consume(queue=queue_name, on_message_callback=celery_event_callback, auto_ack=True)
        rabbitmq_channel.start_consuming()  # starts loop
