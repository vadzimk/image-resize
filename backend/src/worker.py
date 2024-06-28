import json
import os
import tempfile
from contextlib import contextmanager

import pika
from celery import Celery, shared_task
from celery.signals import task_postrun
from celery.utils.log import get_task_logger
from minio import S3Error
from fastapi.encoders import jsonable_encoder

from .settings import server_settings
from .utils import timethis
from .exceptions import S3ObjectNotFoundError
from .models.request.request_model import (TaskState,
                                           ProjectProgressSchema,
                                           ProgressDetail,
                                           ImageVersion,
                                           ProjectFailureSchema)
from .services.minio import s3
from .services.resize_service import resize_with_aspect_ratio


celery = Celery(__name__,
                broker=server_settings.CELERY_BROKER_URL,
                backend=server_settings.CELERY_RESULT_BACKEND,
                include=["src.main", "src.settings", "src.repository.uow"]  # other modules used by celery to include
                )


class CeleryConfig:
    task_create_missing_queues = True
    celery_store_errors_even_if_ignored = True
    task_store_errors_even_if_ignored = True
    task_ignore_result = False
    task_serializer = "pickle"
    result_serializer = "pickle"
    event_serializer = "json"
    accept_content = ["pickle", "application/json", "application/x-python-serialize"]
    result_accept_content = ["pickle", "application/json", "application/x-python-serialize"]


celery.config_from_object(CeleryConfig)
celery.set_default()  # to use shared_task
celery_logger = get_task_logger(__name__)

queue_name = "task_notifications"  # also called routing_key or channel or event_type or event_name or topic or queue


@contextmanager
def rabbitmq_channel_connection():
    rabbitmq_connection = pika.BlockingConnection(pika.URLParameters(server_settings.CELERY_BROKER_URL))
    rabbitmq_channel = rabbitmq_connection.channel()
    rabbitmq_channel.queue_declare(queue=queue_name)
    try:
        yield rabbitmq_channel, rabbitmq_connection
    finally:
        if "rabbitmq_channel" in locals() and rabbitmq_channel.is_open:
            requeued_messages = rabbitmq_channel.cancel()
            celery_logger.warning(f"Requeued messages {requeued_messages}")
            rabbitmq_channel.close()
        if "rabbitmq_connection" in locals() and rabbitmq_connection.is_open:
            rabbitmq_connection.close()


@shared_task
@timethis
def create_versions(object_name_original: str) -> ProjectProgressSchema:
    project_id, basename = object_name_original.rsplit("/")
    basename_wo_ext, ext = basename.rsplit(".")
    input_file_name_less = basename_wo_ext.replace("_original", "")
    sizes = {
        ImageVersion.thumb: (150, 120),
        ImageVersion.big_thumb: (700, 700),
        ImageVersion.big_1920: (1920, 1080),
        ImageVersion.d2500: (2500, 2500)
    }
    versions = {ImageVersion.original: object_name_original}
    response = None
    try:
        response = s3.get_object(bucket_name=server_settings.MINIO_BUCKET_NAME, object_name=object_name_original)
        # Read data from response.
        with tempfile.NamedTemporaryFile(delete=True) as temp_input_file:
            temp_input_file.write(response.data)
            with tempfile.TemporaryDirectory() as temp_dir:
                for index, (size_key, size_value) in enumerate(sizes.items()):
                    destination_name = f"{input_file_name_less}_{size_key}.{ext}"
                    destination_temp_path = os.path.join(temp_dir, destination_name)
                    resize_with_aspect_ratio(temp_input_file, destination_temp_path,
                                             size_value)  # must use temporary file
                    object_name = f"{project_id}/{input_file_name_less}_{size_key}.{ext}"
                    s3.fput_object(bucket_name=server_settings.MINIO_BUCKET_NAME, object_name=object_name, file_path=destination_temp_path)
                    versions[size_key] = object_name

                    message = ProjectProgressSchema(
                        project_id=project_id,
                        versions=versions,
                        state=TaskState.PROGRESS,
                        progress=ProgressDetail(done=(index + 1), total=len(sizes.keys()))
                    )

                    notify_client(message)
            # will close temp_input_file
    except S3Error as e:
        if e.code == "NoSuchKey":
            celery_logger.error(f"Object {object_name_original} does not exist in bucket {server_settings.MINIO_BUCKET_NAME}")
        raise S3ObjectNotFoundError(object_name_original, server_settings.MINIO_BUCKET_NAME) from e
    finally:
        if response is not None:
            response.close()
            response.release_conn()
    return message


def notify_client(message):
    celery_logger.info(f"notify_client:message: {message}")
    with rabbitmq_channel_connection() as (rabbitmq_channel, rabbitmq_connection):
        rabbitmq_channel.basic_publish(exchange='',
                                       routing_key=queue_name,
                                       body=json.dumps(jsonable_encoder(message)))


@task_postrun.connect
def task_postrun_handler(task_id, retval:ProjectProgressSchema, state, **kwargs):
    if isinstance(retval, Exception):
        message = ProjectFailureSchema(task_id=task_id, state=TaskState.FAILURE, error=str(retval))
        celery_logger.error(message)
        notify_client(message)
    else:
        retval.state= state
        notify_client(retval)
