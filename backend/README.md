# Notes

start docker-compose  
```shell
set -o allexport
source .env
set +o allexport
docker-compose up -d
```

https://pypi.org/project/minio/


https://min.io/docs/minio/linux/developers/python/API.html#listen-bucket-notification-bucket-name-prefix-suffix-events-s3-objectcreated-s3-objectremoved-s3-objectaccessed  
```python
with client.listen_bucket_notification(
    "my-bucket",
    prefix="my-prefix/",
    events=["s3:ObjectCreated:*", "s3:ObjectRemoved:*"],
) as events:
    for event in events:
        print(event)
```