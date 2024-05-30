import os

from dotenv import load_dotenv
from minio import Minio

load_dotenv()
MINIO_HOSTNAME = "localhost:9000"

s3 = Minio(
    MINIO_HOSTNAME,
    secure=False,
    access_key=os.getenv("MINIO_ROOT_USER"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD")
)


def make_bucket_if_not_exist(bucket_name: str):
    if not s3.bucket_exists(bucket_name):
        s3.make_bucket(bucket_name)


make_bucket_if_not_exist("images")
