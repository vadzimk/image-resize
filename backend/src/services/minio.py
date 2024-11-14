from datetime import timedelta

from minio import Minio

from ..settings import server_settings

# https://min.io/docs/minio/linux/developers/python/API.html

s3 = Minio(
    endpoint=server_settings.MINIO_HOSTNAME,
    access_key=server_settings.MINIO_ROOT_USER,
    secret_key=server_settings.MINIO_ROOT_PASSWORD,
    secure=False,
)


def make_bucket_if_not_exist(bucket_name: str):
    if not s3.bucket_exists(bucket_name):
        s3.make_bucket(bucket_name)


make_bucket_if_not_exist(server_settings.MINIO_BUCKET_NAME)


def get_presigned_url_put(object_name):
    url = s3.get_presigned_url(
        "PUT",
        server_settings.MINIO_BUCKET_NAME,
        object_name,
        expires=timedelta(days=1),
        # response_headers={"response-content-type": "application/json"},
    )
    return url


def get_presigned_url_get(object_name: str):
    response_headers = {
        "response-content-type": "application/octet-stream",
        "response-content-disposition": f'attachment; filename="{object_name.replace("/", "_")}"'
    }
    url = s3.presigned_get_object(
        server_settings.MINIO_BUCKET_NAME,
        object_name,
        expires=timedelta(days=7),
        response_headers=response_headers
    )
    return url

