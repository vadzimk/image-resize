import logging
import time
from functools import wraps
from typing import Any, List, Union, Type

from pydantic import BaseModel, TypeAdapter

logger = logging.getLogger(__name__)


def timethis(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        r = func(*args, **kwargs)
        end = time.time()
        elapsed = end - start
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        milliseconds = int((elapsed - int(elapsed)) * 1000)
        message = f"{func.__name__}-->{hours}h:{minutes}m:{seconds}s:{milliseconds}ms"
        print(message)
        logger.debug(message)
        return r

    return wrapper


def validate_message(message: Any, candidate_models: List[Type[BaseModel]]) -> Any:

    """ Validate message against candidate_models """
    union_type = candidate_models[0] if len(candidate_models) == 1 else Union[tuple(candidate_models)]
    type_adapter = TypeAdapter(union_type)
    response_model = type_adapter.validate_python(message)
    return response_model
