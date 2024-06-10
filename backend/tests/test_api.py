import asyncio
import json
import re
from pprint import pprint
import pytest
from websockets import connect
from ..src.services.minio import s3, bucket_name
from .utils import (upload_file,
                    get_images_s3_upload_link_and_project_id,
                    cleanup_s3_objects,
                    Subscription,
                    trigger_original_file_upload
                    )

from ..src.schemas import Project


@pytest.mark.skip
def test_upload_file_endpoint_returns_Project():
    image_file_path = "./tests/photo.jpeg"
    res = upload_file(image_file_path)
    print("response: ", end='')
    pprint(res.json())
    assert res.status_code == 201
    project_response = Project.model_validate_json(res.text)
    assert project_response.project_id is not None
    objects = project_response.versions.values()
    print("objects", objects)
    assert len(objects) == 5  # number of file versions
    all_objects_in_project = list(
        s3.list_objects(bucket_name=bucket_name, prefix=str(project_response.project_id), recursive=True))
    cleanup_s3_objects([o.object_name for o in all_objects_in_project])


# @pytest.mark.skip
@pytest.mark.asyncio
async def test_websocket_can_subscribe_to_key_prefix_receive_subscribed_events_using_file_upload():
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
    all_objects_in_project = list(s3.list_objects(bucket_name=bucket_name, prefix=project_id, recursive=True))
    cleanup_s3_objects([o.object_name for o in all_objects_in_project])


# @pytest.mark.skip
@pytest.mark.asyncio
@pytest.mark.timeout(10)  # times out when versions are not removed
async def test_when_new_file_posted_receives_subscribed_events_and_versions_are_created_in_s3():
    # post original
    image_file_path = "./tests/photo.jpeg"
    upload_link, project_id = get_images_s3_upload_link_and_project_id(image_file_path)
    print("project_id", project_id)

    asyncio.create_task(trigger_original_file_upload(image_file_path, upload_link))

    versions = ["original", "big_thumb", "thumb", "big_1920", "d2500"]
    # subscribe to ws s3 events
    async with Subscription(project_id) as websocket:
        while len(versions) > 0:
            response = await websocket.recv()  # get the next object message
            message = json.loads(response)
            s3object_key = message['s3']['object']['key']
            assert s3object_key.startswith(project_id)

            # verify receipt of websocket messages about all versions created
            if 's3:ObjectCreated' in message['eventName']:
                for version in versions:
                    pattern = fr'_{version}(?=.*(?:[^.]*\.(?!.*\.))|$)'
                    if re.search(pattern, s3object_key):
                        print("removing", version)
                        versions.remove(version)
        # print("Receiving last")
        # response = await websocket.recv()  # get the next object message
        # message = json.loads(response)
        # print(message)
    assert len(versions) == 0  # all versions were created

    # check that versions are created in s3 by listing s3 objects
    all_objects_in_project = list(s3.list_objects(bucket_name=bucket_name, prefix=project_id, recursive=True))
    print("objects", [o.object_name for o in all_objects_in_project])
    assert len(all_objects_in_project) == 5  # number of versions of file
    cleanup_s3_objects([o.object_name for o in all_objects_in_project])


# @pytest.mark.skip
@pytest.mark.asyncio
async def test_websocket_can_unsubscribe():
    # post original
    image_file_path = "./tests/photo.jpeg"
    upload_link, project_id = get_images_s3_upload_link_and_project_id(image_file_path)
    print("project_id", project_id)

    asyncio.create_task(trigger_original_file_upload(image_file_path, upload_link))
    async with Subscription(project_id) as websocket:
        response = await websocket.recv()
        message = json.loads(response)
        s3object_key = message['s3']['object']['key']
        assert s3object_key.startswith(project_id)
        await websocket.send(json.dumps({"unsubscribe": project_id}))
        response = await websocket.recv()
        res = json.loads(response)
        assert res['status'] == "OK"
        assert res['unsubscribe'] == project_id
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(websocket.recv(), timeout=2)  # no more messages from websocket after unsubscribe
    all_objects_in_project = list(s3.list_objects(bucket_name=bucket_name, prefix=project_id, recursive=True))
    cleanup_s3_objects([o.object_name for o in all_objects_in_project])

# TODO implement Celery
# websocket listen when the status changes and post to subscribers
