import asyncio
import logging
from asyncio import AbstractEventLoop
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI
from minio import S3Error

from .websocket_manager import ws_manager
from .api import router
from .services.minio import s3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Logger connected")

logger.info(f"Minio: {'connected' if s3.bucket_exists('images') else 'NOT connected'}")

executor = ThreadPoolExecutor(max_workers=1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # before yield: same as @app.on_event('startup')
    loop = asyncio.get_event_loop()
    executor.submit(listen_to_s3_events, loop)
    yield
    # after yield: same as @app.on_event('shutdown')
    executor.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)
app.include_router(router)


def listen_to_s3_events(loop: AbstractEventLoop):
    async def publish_event(message: dict):
        await ws_manager.broadcast(message)

    try:
        with s3.listen_bucket_notification("images", events=["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]) as events:
            for event in events:
                logger.info(event)
                asyncio.run_coroutine_threadsafe(publish_event(event), loop=loop)
    except S3Error as err:
        logger.error(f"S3 Error: {err}")



