import json

from celery.utils.log import get_task_logger
from fastapi.encoders import jsonable_encoder

from ..services.message_broker import rabbitmq_channel_connection
from ..settings import server_settings

celery_logger = get_task_logger(__name__)


def notify_client(message):
    celery_logger.debug(message)
    with rabbitmq_channel_connection() as (rabbitmq_channel, rabbitmq_connection):
        rabbitmq_channel.basic_publish(exchange='',
                                       routing_key=server_settings.task_notifications_queue,
                                       body=json.dumps(jsonable_encoder(message)))
