import json
import logging
import traceback
from pathlib import Path

from minio import S3Error
from asyncio import AbstractEventLoop

from ..services.message_broker import rabbitmq_channel_connection
from ..settings import server_settings
from ..utils import validate_message
from ..services.message_bus import bus
from ..models.domain.events import CeleryTaskUpdated, OriginalUploaded
from ..models.request.request_model import TaskState, ProjectProgressSchema, GetProjectSchema, ImageVersion, \
    ProjectFailureSchema
from ..services.minio import s3

logger = logging.getLogger(__name__)


def listen_create_s3_events_and_update_db_and_start_celery_tasks(loop: AbstractEventLoop):
    def handle_s3_event(event: dict):
        for record in event.get("Records", []):
            s3_object_key = record["s3"]["object"]["key"]
            logger.debug(f'Event: {record["eventName"]}, object_key: {s3_object_key}')
            is_endswith_original = Path(s3_object_key).stem.endswith('_original')
            if is_endswith_original:
                logger.debug(f"Found original object_key: {s3_object_key}")
                original_object_key = s3_object_key
                original_uploaded_event = OriginalUploaded(
                    message=GetProjectSchema(
                        object_prefix=original_object_key.split("/")[0],
                        state=TaskState.GOT_ORIGINAL,
                        versions={ImageVersion.original: original_object_key}
                    ))
                bus.handle(original_uploaded_event)

    try:
        # create file versions when original is uploaded
        with s3.listen_bucket_notification(bucket_name=server_settings.MINIO_BUCKET_NAME,
                                           events=["s3:ObjectCreated:*"]) as events:
            logger.debug("About to handle s3 events")
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
    logger.debug(f"Entered")

    def celery_event_callback(ch, method, properties, body):
        try:
            logger.debug(f"args: body: {body}")
            message = validate_message(json.loads(body), [ProjectProgressSchema, ProjectFailureSchema])
            logger.debug(f"message = {message}")
            bus.handle(CeleryTaskUpdated(message=message))

        except Exception:
            logger.error(f"Rabbitmq callback error:\n{traceback.format_exc()}")
            raise

    with rabbitmq_channel_connection() as (rabbitmq_channel, rabbitmq_connection):
        logger.debug(
            f"To publish: rabbitmq_channel: {rabbitmq_channel is not None}; rabbitmq_connection: {rabbitmq_connection is not None}")
        rabbitmq_channel.basic_consume(queue=server_settings.task_notifications_queue,
                                       on_message_callback=celery_event_callback, auto_ack=True)
        rabbitmq_channel.start_consuming()  # starts loop
