import json
import logging

from minio import S3Error
import traceback
from asyncio import AbstractEventLoop

from .settings import server_settings
from .utils import validate_message
from .services.message_bus import bus
from .models.domain.events import CeleryTaskUpdated, OriginalUploaded
from .models.request.request_model import TaskState, ProjectProgressSchema, GetProjectSchema, ImageVersion, ProjectFailureSchema
from .worker import rabbitmq_channel_connection, queue_name
from .services.minio import s3

logger = logging.getLogger(__name__)


def listen_create_s3_events_and_update_db_and_start_celery_tasks(loop: AbstractEventLoop):
    def handle_s3_event(event: dict):
        for record in event.get("Records", []):
            s3_object_key = record["s3"]["object"]["key"]
            logger.debug(f'listen_create_s3_events_to_upload_versions: {record["eventName"]}: {s3_object_key}')
            if s3_object_key.rsplit(".")[0].endswith("_original"):
                logger.debug(f"listen_create_s3_events_to_upload_versions: found original {s3_object_key}")
                original_object_key = s3_object_key
                original_uploaded_event = OriginalUploaded(
                    message=GetProjectSchema(
                        project_id=original_object_key.split("/")[0],
                        state=TaskState.GOTORIGINAL,
                        versions={ImageVersion.original: original_object_key}
                    ))
                bus.handle(original_uploaded_event)

    try:
        # create file versions when original is uploaded
        with s3.listen_bucket_notification(bucket_name=server_settings.MINIO_BUCKET_NAME, events=["s3:ObjectCreated:*"]) as events:
            logger.debug("ENTERED listen_create_s3_events_and_update_db_and_start_celery_tasks")
            for event in events:
                handle_s3_event(event)

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
            logger.debug(f"Entered listen_celery_task_notifications_queue:celery_event_callback:body: {body}")
            message = validate_message(json.loads(body), [ProjectProgressSchema, ProjectFailureSchema])
            logger.debug(f"message = {message}")
            bus.handle(CeleryTaskUpdated(message=message))

        except Exception:
            logger.error(f"Rabbitmq callback error:\n{traceback.format_exc()}")
            raise

    with rabbitmq_channel_connection() as (rabbitmq_channel, rabbitmq_connection):
        logger.debug(
            f"listen_celery_task_notifications_queue_to_publish: rabbitmq_channel: {rabbitmq_channel is not None}; rabbitmq_connection: {rabbitmq_connection is not None}")
        rabbitmq_channel.basic_consume(queue=queue_name, on_message_callback=celery_event_callback, auto_ack=True)
        rabbitmq_channel.start_consuming()  # starts loop

