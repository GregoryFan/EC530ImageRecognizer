import asyncio
import base64
import json
import pytest
from redis.asyncio import Redis
import db_service

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

    db_task = asyncio.create_task(db_service.start())

    message = None
    while message is None or message["type"] != "message":
        message = await pubsub.get_message(timeout=5)  

    assert message is not None, "Did not receive any message on service.ready channel"
    assert message["type"] == "message", f"Expected message type 'message', got {message['type']}"
    assert message["data"] == "db_service", f"Expected data 'db_service', got {message['data']}"

    #cleanup
    db_task.cancel()
    try:
        await db_task
    except asyncio.CancelledError:
        pass

    await pubsub.unsubscribe("service.ready")
    await pubsub.aclose()
    await r.aclose()

@pytest.mark.asyncio
async def test_upload_image():
    message_payload = {
        "data": json.dumps({
            "image_id": "test-image-123",
            "image_data": base64.b64encode(b"fake image bytes").decode("utf-8"),
            "inferences": [{ 
                "label": "cat",
                "vertices": [(10, 10), (100, 10), (100, 100), (10, 100)]
            }]
        })
    }

    # Should complete without raising
    await db_service.upload_image(message_payload)


@pytest.mark.asyncio
async def test_query_image(tmp_path):
    # query_image opens "test.png" hardcoded, so we need it to exist
    test_image = tmp_path / "test.png"
    test_image.write_bytes(b"fake png bytes")

    # Patch the working directory so "test.png" resolves correctly
    import os
    original_dir = os.getcwd()
    os.chdir(tmp_path)

    r = Redis(host='localhost', port=6379, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("query.results")

    # Wait for subscription confirmation
    for _ in range(10):
        msg = await pubsub.get_message(timeout=1)
        if msg and msg["type"] == "subscribe":
            break

    message_payload = {
        "data": json.dumps({
            "similar_image_ids": ["img-1", "img-2"],
            "event_id": "test-event-456"
        })
    }

    handle_task = asyncio.create_task(db_service.query_image(message_payload))
    await handle_task  

    message = None
    for _ in range(10):
        message = await pubsub.get_message(timeout=2)
        if message and message["type"] == "message":
            break

    assert message is not None

    data = json.loads(message["data"])
    assert data["event_id"] == "test-event-456"
    assert "image_data" in data
    assert isinstance(data["image_data"], list)
    assert len(data["image_data"]) > 0

    # Verify the base64 content is valid and decodable
    for img in data["image_data"]:
        decoded = base64.b64decode(img)
        assert len(decoded) > 0


    os.chdir(original_dir)
    await pubsub.unsubscribe("query.results")
    await pubsub.aclose()
    await r.aclose()

