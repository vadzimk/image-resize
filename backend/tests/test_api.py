import asyncio
import json
import os
import re
from pprint import pprint
from typing import List

import httpx
import pytest
from fastapi.testclient import TestClient
from minio.deleteobjects import DeleteObject
from websockets import connect

from ..src.websocket_manager import ws_manager
from ..src.services.minio import s3
from ..src.schemas import Project
from ..src.main import app

client = TestClient(app)


def upload_file(image_file_path):
    assert os.path.exists(image_file_path)
    with open(image_file_path, "rb") as image_file:
        files = {"file": (os.path.basename(image_file_path), image_file, "image/jpeg")}
        return client.post("/uploadfile", files=files)


def cleanup_after_upload_file(objects: List[str]):
    """
    deletes s3 objects form minio storage
    :param objects: list of str of format "e4302caa-dbd7-4743-ba09-241bd48e35f3/photo_original.jpeg"
    """
    errors = s3.remove_objects("images", [DeleteObject(obj) for obj in objects])
    if len(list(errors)) != 0:
        raise AssertionError
    print(f"Cleanup cleanup_after_upload_file. Done. Deleted {len(objects)} objects.")


# @pytest.mark.skip
def test_upload_file_endpoint_returns_Project():
    image_file_path = "./tests/photo.jpeg"
    res = upload_file(image_file_path)
    print("response: ", end='')
    pprint(res.json())
    assert res.status_code == 201
    project_response = Project.model_validate_json(res.text)
    assert project_response.project_id is not None
    cleanup_after_upload_file(res.json().get("versions").values())
    objects = project_response.versions.values()
    # cleanup
    errors = s3.remove_objects("images", [DeleteObject(obj) for obj in objects])
    assert len(list(errors)) == 0


# @pytest.mark.skip
@pytest.mark.asyncio
async def test_websocket_subscribe_to_key_prefix_receives_subscribed_events_using_file_upload():
    """ subscribe events are create and delete object """
    image_file_path = "./tests/photo.jpeg"
    res = upload_file(image_file_path)
    project_id = res.json().get("project_id")

    async def trigger_event():
        cleanup_after_upload_file(res.json().get("versions").values())

    asyncio.create_task(trigger_event())

    async with connect("ws://localhost:8000/ws") as websocket:
        await websocket.send(json.dumps({"subscribe": project_id}))
        res_confirmation = await websocket.recv()  # receive the confirmation message from websocket
        print("res_confirmation", res_confirmation)
        assert json.loads(res_confirmation).get("status", None) == "OK"
        response = await websocket.recv()  # receive the next message from websocket (only the first message)
        # event triggered in the background somewhere here and the recv() unblocks
        message = json.loads(response)
        pprint(message)
        assert message['s3']['object']['key'].startswith(project_id)


@pytest.mark.skip  # using ws_manager does not work in this test
@pytest.mark.asyncio
async def test_websocket_subscribe_to_key_prefix_receives_subscribed_events_using_ws_manager():
    from ..src.main import asyncio as main_asyncio
    print(f"\nRunning in the same event loop : {main_asyncio.get_running_loop() is asyncio.get_running_loop()}")
    test_key_prefix = "9c407d31-150a-4168-b382-77114d5474be"
    test_event = {
        "Records": [
            {
                "eventVersion": "2.0",
                "eventSource": "minio:s3",
                "awsRegion": "",
                "eventTime": "2024-05-31T15:52:16.922Z",
                "eventName": "s3:ObjectRemoved:Delete",
                "userIdentity": {
                    "principalId": "ROOTNAME"
                },
                "requestParameters": {
                    "principalId": "ROOTNAME",
                    "region": "",
                    "sourceIPAddress": "192.168.65.1"
                },
                "responseElements": {
                    "content-length": "116",
                    "x-amz-id-2": "dd9025bab4ad464b049177c95eb6ebf374d3b3fd1af9251148b658df7ac2e3e8",
                    "x-amz-request-id": "17D49DAFEE8ED8EB",
                    "x-minio-deployment-id": "43eb1127-d050-42fe-a338-73efc16f9c0f",
                    "x-minio-origin-endpoint": "http://172.25.0.2:9000"
                },
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "configurationId": "Config",
                    "bucket": {
                        "name": "images",
                        "ownerIdentity": {
                            "principalId": "ROOTNAME"
                        },
                        "arn": "arn:aws:s3:::images"
                    },
                    "object": {
                        "key": f"{test_key_prefix}/photo_d2500.jpeg",
                        "sequencer": "17D49DAFF0F17487"
                    }
                },
                "source": {
                    "host": "192.168.65.1",
                    "port": "",
                    "userAgent": "MinIO (Darwin; x86_64) minio-py/7.2.7"
                }
            }
        ]
    }

    async def trigger_event():
        print("Going to sleep 2s")
        await asyncio.sleep(2)
        print("Event going to trigger")
        await ws_manager.publish(test_event)

    asyncio.create_task(trigger_event())  # run event trigger in the background

    async with connect("ws://localhost:8000/ws") as websocket:
        await websocket.send(json.dumps({"subscribe": test_key_prefix}))
        res_confirmation = await websocket.recv()  # receive the confirmation message from websocket
        print("res_confirmation", res_confirmation)
        assert json.loads(res_confirmation).get("status", None) == "OK"
        response = await websocket.recv()  # receive the next message from websocket  # debug here, it blocks
        message = json.loads(response)
        pprint(message)
        assert True


def test_can_get_new_image_url_and_put_file_from_images_post_endpoint():
    image_file_path = "./tests/photo.jpeg"
    assert os.path.exists(image_file_path)
    filename = os.path.basename(image_file_path)
    res = client.post("/images", json={"filename": filename})
    body = res.json()
    upload_link = body.get('upload_link')
    print("upload_link: ", upload_link)
    assert body['filename'] == filename
    assert upload_link.startswith('http')

    with open(image_file_path, 'rb') as file:
        response = httpx.put(upload_link, content=file, headers={'Content-Type': 'application/json'})
    print('response_text', response.text)
    assert response.status_code == 200
    bucket_name = "images"
    pattern = fr'/{bucket_name}/([^?]+)'
    match = re.search(pattern, upload_link).group(1)
    print('match', match)
    cleanup_after_upload_file([match])
