import upload_service
import asyncio
from redis.asyncio import Redis
import pytest
import json

@pytest.mark.asyncio
async def test_start():
    r = Redis(host='localhost', port=6379, decode_responses=True)
    pubsub = r.pubsub()

    #Subscribe to service.ready to ensure that the main function is running and publishing the ready message
    await pubsub.subscribe("service.ready")

    while True:
        message = await pubsub.get_message(timeout=1)
        if message is not None and message["type"] == "subscribe":
            break

    upload_task = asyncio.create_task(upload_service.start())

    message = None
    while message is None or message["type"] != "message":
        message = await pubsub.get_message(timeout=5)  

    assert message is not None, "Did not receive any message on service.ready channel"
    assert message["type"] == "message", f"Expected message type 'message', got {message['type']}"
    assert message["data"] == "upload_service", f"Expected data 'upload_service', got {message['data']}"

    #cleanup
    upload_task.cancel()
    try:
        await upload_task
    except asyncio.CancelledError:
        pass

    await pubsub.unsubscribe("service.ready")
    await pubsub.aclose()
    await r.aclose()

@pytest.mark.asyncio
async def test_handle_uploaded_image():
    r = Redis(host='localhost', port=6379, decode_responses=True)
    pubsub = r.pubsub()

    await pubsub.subscribe("image.inferrences")

    #start the function
    handle_task = asyncio.create_task(upload_service.handle_uploaded_image(json.dumps({"image_path": "test.png"})))

    #listen for the published message
    message = None
    while message is None or message["type"] != "message":
        message = await pubsub.get_message(timeout=5)
    
    assert message is not None, "Did not receive any message on image.inferrences channel"
    assert message["type"] == "message", f"Expected message type 'message', got {message['type']}"
    data = json.loads(message["data"])
    assert "image_id" in data, "Expected 'image_id' in published data"
    assert "image_data" in data, "Expected 'image_data' in published data"

    #cleanup
    handle_task.cancel()
    try:
        await handle_task
    except asyncio.CancelledError:
        pass
    pubsub.unsubscribe("image.inferrences")
    await pubsub.aclose()
    await r.aclose()
    

