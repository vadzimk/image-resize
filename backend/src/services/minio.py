import os
from datetime import timedelta

from dotenv import load_dotenv
from minio import Minio

load_dotenv()
MINIO_HOSTNAME = "localhost:9000"
bucket_name = "images"

s3 = Minio(
    MINIO_HOSTNAME,
    secure=False,
    access_key=os.getenv("MINIO_ROOT_USER"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD")
)


def make_bucket_if_not_exist(bucket_name: str):
    if not s3.bucket_exists(bucket_name):
        s3.make_bucket(bucket_name)


def get_presigned_url_put(object_name):
    url = s3.get_presigned_url(
        "PUT",
        bucket_name,
        object_name,
        expires=timedelta(days=1),
        response_headers={"response-content-type": "application/json"},
    )
    return url


make_bucket_if_not_exist("images")
