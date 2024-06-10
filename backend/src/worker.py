import json
import os
import tempfile
from contextlib import contextmanager

import pika
from celery import Celery, shared_task
from celery.signals import task_postrun
from celery.utils.log import get_task_logger
from dotenv import load_dotenv
from pika import PlainCredentials

from .services.minio import s3, bucket_name
from .services.resize_service import resize_with_aspect_ratio

load_dotenv()

celery = Celery(__name__,
                broker=os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@127.0.0.1:5672"),
                backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/0"),
                include=["src.main"]  # other modules used by celery to include
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

queue_name = "task_notifications"


@contextmanager
def rabbitmq_channel_connection():
    try:
        rabbitmq_connection = pika.BlockingConnection(pika.ConnectionParameters(
            host="127.0.0.1",
            port=5672,
            credentials=PlainCredentials(username="guest", password="guest")))
        rabbitmq_channel = rabbitmq_connection.channel()
        rabbitmq_channel.queue_declare(queue=queue_name)
        yield rabbitmq_channel, rabbitmq_connection
    finally:
        if "rabbitmq_channel" in locals() and rabbitmq_channel.is_open:
            rabbitmq_channel.close()
        if "rabbitmq_connection" in locals() and rabbitmq_connection.is_open:
            rabbitmq_connection.close()


@shared_task
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
    return {"project_id": project_id, "versions": versions}


def notify_client(message: dict):
    with rabbitmq_channel_connection() as (rabbitmq_channel, rabbitmq_connection):
        rabbitmq_channel.basic_publish(exchange='',
                                       routing_key=queue_name,
                                       body=json.dumps(message))


@task_postrun.connect
def task_postrun_handler(task_id, retval: dict, state, **kwargs):
    message = retval.copy()
    message.update({"state": state})
    notify_client(message)
    celery_logger.info(json.dumps(message))


