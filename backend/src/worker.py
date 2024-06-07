import os
import tempfile

from celery import Celery
from dotenv import load_dotenv
from .services.minio import s3, bucket_name
from .services.resize_service import resize_with_aspect_ratio


load_dotenv()

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/0")


@celery.task
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
