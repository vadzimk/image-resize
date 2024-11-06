from celery import Celery
from celery.signals import task_postrun
from celery.utils.log import get_task_logger

from .utils import notify_client
from ..settings import server_settings

from ..models.request.request_model import (TaskState,
                                          ProjectProgressSchema,

                                          ProjectFailureSchema)

celery = Celery(__name__,
                broker=server_settings.CELERY_BROKER_URL,
                backend=server_settings.CELERY_RESULT_BACKEND,
                include=["src.main", "src.settings", "src.unit_of_work.mongo_uow"]  # other modules used by celery to include
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


@task_postrun.connect
def task_postrun_handler(task_id, retval: ProjectProgressSchema, state, **kwargs):
    if isinstance(retval, Exception):
        message = ProjectFailureSchema(task_id=task_id, state=TaskState.FAILURE, error=str(retval))
        celery_logger.error(message)
        notify_client(message)
    else:
        retval.state = state
        notify_client(retval)
