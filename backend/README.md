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

PASSED
tests/test_api.py::test_upload_file_returns_Project create_upload_file-->0h:0m:1s:937ms
response: {'project_id': '85653a59-b795-43e3-980f-7b314b8245e5',
 'state': 'init',
 'versions': {'big_1920': '85653a59-b795-43e3-980f-7b314b8245e5/photo_big_1920.jpeg',
              'big_thumb': '85653a59-b795-43e3-980f-7b314b8245e5/photo_big_thumb.jpeg',
              'd2500': '85653a59-b795-43e3-980f-7b314b8245e5/photo_d2500.jpeg',
              'original': '85653a59-b795-43e3-980f-7b314b8245e5/photo_original.jpeg',
              'thumb': '85653a59-b795-43e3-980f-7b314b8245e5/photo_thumb.jpeg'}}

