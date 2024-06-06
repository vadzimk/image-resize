import asyncio
import json
from pprint import pprint

import pytest
from websockets import connect
from ..src.services.minio import s3
from minio.deleteobjects import DeleteObject
from .utils import (upload_file,
                    get_images_s3_upload_link_and_project_id,
                    cleanup_s3_objects,
                    s3_upload_link_put_file
                    )

from ..src.schemas import Project

bucket_name = "images"


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
