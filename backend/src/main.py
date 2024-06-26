import logging
import threading
import asyncio
from contextlib import asynccontextmanager
from typing import Callable, List

from fastapi import FastAPI

from .api import router
from .services.minio import s3, bucket_name
from .services.message_bus import bus
from .listeners import (
    listen_create_s3_events_and_update_db_and_start_celery_tasks,
    listen_celery_task_notifications_queue)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"Minio: {'connected' if s3.bucket_exists(bucket_name) else 'NOT connected'}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # before yield: same as @app.on_event('startup')
    loop = asyncio.get_event_loop()
    bus.loop = loop
    listeners: List[Callable] = [
        listen_create_s3_events_and_update_db_and_start_celery_tasks,
        listen_celery_task_notifications_queue
    ]
    threads = []
    for listener in listeners:
        thread = threading.Thread(target=listener, args=(loop,))
        thread.daemon = True  # shuts down threads when main shuts down
        thread.start()
        threads.append(thread)
    yield
    # after yield: same as @app.on_event('shutdown')
    for thread in threads:
        thread.join(timeout=1)


app = FastAPI(lifespan=lifespan)

app.include_router(router)
