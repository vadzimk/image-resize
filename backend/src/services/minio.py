from datetime import timedelta

from minio import Minio, error as MinioError

from ..settings import server_settings

# https://min.io/docs/minio/linux/developers/python/API.html
# https://github.com/minio/minio-js/issues/833
# presigned url must be requested by going through the same path as the client, ie. through nginx
# but that is only possible if you have public ip on it ( or changing hosts file locally)
s3 = Minio(
    endpoint=server_settings.MINIO_URL,
    access_key=server_settings.MINIO_ROOT_USER,
    secret_key=server_settings.MINIO_ROOT_PASSWORD,
    secure=False,
)


def make_bucket_if_not_exist(bucket_name: str):
    if not s3.bucket_exists(bucket_name):
        s3.make_bucket(bucket_name)


make_bucket_if_not_exist(server_settings.MINIO_BUCKET_NAME)


def get_presigned_url_put(object_name: str):
    try:
        return _generate_presigned_url(object_name)
    except MinioError.S3Error as e:
        if e.code == 'NoSuchBucket':
            make_bucket_if_not_exist(server_settings.MINIO_BUCKET_NAME)
            return _generate_presigned_url(object_name)
        else:
            raise


def _generate_presigned_url(object_name: str):
    return s3.get_presigned_url(
        "PUT",
        server_settings.MINIO_BUCKET_NAME,
        object_name,
        expires=timedelta(days=1),
        # response_headers={"response-content-type": "application/json"},
    )


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
