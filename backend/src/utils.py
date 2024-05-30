import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def timethis(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        r = func(*args, **kwargs)
        end = time.time()
        elapsed = end - start
        print(end - start)
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        milliseconds = int((elapsed - int(elapsed)) * 1000)
        logger.info(f"{func.__name__}-->{hours}h:{minutes}m:{seconds}s:{milliseconds}ms")
        return r

    return wrapper
