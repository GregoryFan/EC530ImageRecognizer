import asyncio
import base64
import json
import pytest
from redis.asyncio import Redis
import upload_service

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
async def test_handle_uploaded_image(tmp_path):
    test_image = tmp_path / "test.png"
    test_image.write_bytes(b"fake png bytes")

    r = Redis(host='localhost', port=6379, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("image.inferrences")

    # Wait until Redis confirms the subscription before proceeding
    for _ in range(10):
        msg = await pubsub.get_message(timeout=1)
        if msg and msg["type"] == "subscribe":
            break

    message_payload = {
    "data": json.dumps({
        "image_path": str(test_image),
        "event_id": "test-event-123",  
        "inferences": {"test", [1 ,2 ,3 ,4]}
    })
}
    handle_task = asyncio.create_task(
        upload_service.handle_uploaded_image(message_payload)
    )

    # Give the task a moment to run and publish
    await asyncio.sleep(0.1)

    # Listen for the published message
    message = None
    for _ in range(10):
        message = await pubsub.get_message(timeout=2)
        if message and message["type"] == "message":
            break

    assert message is not None, "Did not receive any message on image.inferrences channel"
    assert message["type"] == "message"

    data = json.loads(message["data"])
    assert "event_id" in data
    assert data["event_id"] == "test-event-123"
    assert "image_id" in data
    assert "image_data" in data

    expected = base64.b64encode(b"fake png bytes").decode("utf-8")
    assert data["image_data"] == expected

    expected = base64.b64encode(b"fake png bytes").decode("utf-8")
    assert data["image_data"] == expected

    handle_task.cancel()
    try:
        await handle_task
    except asyncio.CancelledError:
        pass

    await pubsub.unsubscribe("image.inferrences")
    await pubsub.aclose()
    await r.aclose()