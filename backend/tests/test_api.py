import asyncio
import json
import os
import re
from pprint import pprint
from typing import List, Tuple

import httpx
import pytest
from fastapi.testclient import TestClient
from minio.deleteobjects import DeleteObject
from websockets import connect

from ..src.websocket_manager import ws_manager
from ..src.services.minio import s3
from ..src.schemas import Project, ProjectCreate
from ..src.main import app

client = TestClient(app)
bucket_name = "images"


def upload_file(image_file_path):
    assert os.path.exists(image_file_path)
    with open(image_file_path, "rb") as image_file:
        files = {"file": (os.path.basename(image_file_path), image_file, "image/jpeg")}
        return client.post("/uploadfile", files=files)


def cleanup_s3_objects(objects: List[str]):
    """
    deletes s3 objects form minio storage
    :param objects: list of str of format "e4302caa-dbd7-4743-ba09-241bd48e35f3/photo_original.jpeg"
    """
    errors = s3.remove_objects("images", [DeleteObject(obj) for obj in objects])
    if len(list(errors)) != 0:
        raise AssertionError
    print(f"cleanup_s3_objects: Done. Deleted {len(objects)} objects.")


# @pytest.mark.skip
def test_upload_file_endpoint_returns_Project():
    image_file_path = "./tests/photo.jpeg"
    res = upload_file(image_file_path)
    print("response: ", end='')
    pprint(res.json())
    assert res.status_code == 201
    project_response = Project.model_validate_json(res.text)
    assert project_response.project_id is not None
    cleanup_s3_objects(res.json().get("versions").values())
    objects = project_response.versions.values()
    print("objects", objects)
    assert len(objects) == 5  # number of file versions
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
        await asyncio.sleep(1)  # wait for the client to subscribe
        print("----------> triggered event")
        cleanup_s3_objects(res.json().get("versions").values())

    asyncio.create_task(trigger_event())

    async with connect("ws://localhost:8000/ws") as websocket:
        await websocket.send(json.dumps({"subscribe": project_id}))
        res_confirmation = await websocket.recv()  # receive the confirmation message from websocket
        print("res_confirmation", res_confirmation)
        assert json.loads(res_confirmation).get("status") == "OK"
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


def get_images_s3_upload_link_and_project_id(image_file_path) -> Tuple[str, str]:
    assert os.path.exists(image_file_path)
    filename = os.path.basename(image_file_path)
    res = client.post("/images", json={"filename": filename})
    project_response = ProjectCreate.model_validate_json(res.text)
    assert project_response.upload_link.startswith('http')
    assert project_response.filename == filename
    return project_response.upload_link, str(project_response.project_id)


def s3_upload_link_put_file(image_file_path, upload_link):
    with open(image_file_path, 'rb') as file:
        response = httpx.put(upload_link, content=file, headers={'Content-Type': 'application/json'})
    return response


# @pytest.mark.skip
# def test_can_get_new_image_url_and_put_file_using_images_post_endpoint():
#     image_file_path = "./tests/photo.jpeg"
#     upload_link, project_id = get_images_s3_upload_link_and_project_id(image_file_path)
#     response = s3_upload_link_put_file(image_file_path, upload_link)
#     print('project_id', project_id)
#     assert response.status_code == 200
#     all_objects_in_project = list(s3.list_objects(bucket_name=bucket_name, prefix=project_id, recursive=True))
#     cleanup_s3_objects([o.object_name for o in all_objects_in_project])


# TODO when all others skipped this one works fine, but when all are run, this one fails
# @pytest.mark.skip
@pytest.mark.asyncio
async def test_when_new_file_posted_versions_are_created_in_s3():
    # post original
    image_file_path = "./tests/photo.jpeg"
    upload_link, project_id = get_images_s3_upload_link_and_project_id(image_file_path)
    print("project_id", project_id)
    async def trigger_original_file_upload():
        await asyncio.sleep(1)  # wait for client to subscribe
        res = s3_upload_link_put_file(image_file_path, upload_link)
        assert res.status_code == 200

    asyncio.create_task(trigger_original_file_upload())

    # subscribe to ws s3 events
    async with connect("ws://localhost:8000/ws") as websocket:
        await websocket.send(json.dumps({"subscribe": project_id}))
        res_confirmation = await websocket.recv()
        assert json.loads(res_confirmation).get("status") == "OK"
        response = await websocket.recv()  # one object created - original
        message = json.loads(response)
        print()
        pprint(message)
        s3object_key = message['s3']['object']['key']
        assert s3object_key.startswith(project_id)

    # check that versions are created in s3
    await asyncio.sleep(2)  # wait for the versions to be created in s3
    all_objects_in_project = list(s3.list_objects(bucket_name=bucket_name, prefix=project_id, recursive=True))
    print("objects", [o.object_name for o in all_objects_in_project])
    assert len(all_objects_in_project) == 5  # number of versions of file
    cleanup_s3_objects([o.object_name for o in all_objects_in_project])
