import logging
import threading
import asyncio
from contextlib import asynccontextmanager
from typing import Callable, List

from fastapi import FastAPI

from .api.api import router as http_router
from .api.ws import router as ws_router
from .services.websocket_manager import ws_manager
from .settings import server_settings

from .services.minio import s3
from .services.message_bus import bus
from .services.background_listeners import (
    listen_create_s3_events_and_update_db_and_start_celery_tasks,
    listen_celery_task_notifications_queue)
from .utils import setup_logging

setup_logging(logging.INFO, logger=logging.getLogger())

logging.getLogger('pymongo').setLevel(logging.INFO)
logging.getLogger('pika').setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger.info(f"Minio: {'connected' if s3.bucket_exists(server_settings.MINIO_BUCKET_NAME) else 'NOT connected'}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # before yield: same as @app.on_event('startup')
    loop = asyncio.get_event_loop()
    websocket_pubsub_task = loop.create_task(ws_manager.handle_pubsub_events()) # listen for websocket events in the server pool
    bus.loop = loop
    listeners: List[Callable] = [
        listen_create_s3_events_and_update_db_and_start_celery_tasks,
        listen_celery_task_notifications_queue
    ]
    threads = []
    # Start each listener in a daemon thread
    for listener in listeners:
        thread = threading.Thread(target=listener, args=(loop,))
        thread.daemon = True  # shuts down threads when main shuts down
        thread.start()
        threads.append(thread)
    try:
        yield  # app is running
        # after yield: same as @app.on_event('shutdown')
    finally:
        websocket_pubsub_task.cancel()
        try:
            await websocket_pubsub_task  # Ensure the task finalizes properly
        except asyncio.CancelledError:
            pass
        for thread in threads:
            thread.join(timeout=1)


app = FastAPI(lifespan=lifespan)

app.include_router(http_router, prefix='/api')
app.include_router(ws_router)
