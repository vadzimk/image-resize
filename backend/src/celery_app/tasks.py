from pathlib import Path

from celery import shared_task
from celery.utils.log import get_task_logger
from minio import S3Error
import os
import tempfile
from ..celery_app.utils import notify_client
from ..exceptions import S3ObjectNotFoundError
from ..utils import timethis

from ..models.request.request_model import (TaskState,
                                            ProjectProgressSchema,
                                            ProgressDetail,
                                            ImageVersion,
                                            )
from ..settings import server_settings
from ..services.minio import s3
from ..services.resize_service import resize_with_aspect_ratio

celery_logger = get_task_logger(__name__)


@shared_task
@timethis
def create_versions(object_name_original: str) -> ProjectProgressSchema:
    object_prefix = str(Path(object_name_original).parent)
    stem = Path(object_name_original).stem
    suffix = Path(object_name_original).suffix
    input_file_name_base = ''.join(stem.rsplit('_original', 1))  # replace last occurrence of _original with ''
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
                    destination_name = f"{input_file_name_base}_{size_key}{suffix}"
                    destination_temp_path = os.path.join(temp_dir, destination_name)
                    resize_with_aspect_ratio(temp_input_file, destination_temp_path,
                                             size_value)  # must use temporary file
                    object_name = f"{object_prefix}/{input_file_name_base}_{size_key}{suffix}"
                    s3.fput_object(bucket_name=server_settings.MINIO_BUCKET_NAME, object_name=object_name,
                                   file_path=destination_temp_path)
                    versions[size_key] = object_name

                    message = ProjectProgressSchema(
                        object_prefix=object_prefix,
                        versions=versions,
                        state=TaskState.PROGRESS,
                        progress=ProgressDetail(done=(index + 1), total=len(sizes.keys()))
                    )

                    notify_client(message)
            # will close temp_input_file
    except S3Error as e:
        if e.code == "NoSuchKey":
            celery_logger.error(
                f"Object {object_name_original} does not exist in bucket {server_settings.MINIO_BUCKET_NAME}")
        raise S3ObjectNotFoundError(object_name_original, server_settings.MINIO_BUCKET_NAME) from e
    finally:
        if response is not None:
            response.close()
            response.release_conn()
    return message
