# Rabbitmq message broker
import logging
from contextlib import contextmanager, asynccontextmanager
import pika
from ..settings import server_settings
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


@contextmanager
def rabbitmq_channel_connection():
    rabbitmq_connection = pika.BlockingConnection(pika.URLParameters(server_settings.CELERY_BROKER_URL))
    rabbitmq_channel = rabbitmq_connection.channel()
    rabbitmq_channel.queue_declare(queue=server_settings.task_notifications_queue)
    try:
        yield rabbitmq_channel, rabbitmq_connection
    finally:
        if "rabbitmq_channel" in locals() and rabbitmq_channel.is_open:
            requeued_messages = rabbitmq_channel.cancel()
            logger.warning(f"Requeued messages {requeued_messages}")
            rabbitmq_channel.close()
        if "rabbitmq_connection" in locals() and rabbitmq_connection.is_open:
            rabbitmq_connection.close()


@asynccontextmanager
async def redis_connection():
    redis_client = Redis.from_url(server_settings.CELERY_RESULT_BACKEND)
    yield redis_client
    await redis_client.aclose()


redis_client = Redis.from_url(server_settings.CELERY_RESULT_BACKEND)
