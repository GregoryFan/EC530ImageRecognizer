import asyncio
import base64
import json
import pytest
from redis.asyncio import Redis
import vector_db

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

    vector_db_task = asyncio.create_task(vector_db.start())

    message = None
    while message is None or message["type"] != "message":
        message = await pubsub.get_message(timeout=5)  

    assert message is not None, "Did not receive any message on service.ready channel"
    assert message["type"] == "message", f"Expected message type 'message', got {message['type']}"
    assert message["data"] == "vector_db", f"Expected data 'vector_db', got {message['data']}"

    #cleanup
    vector_db_task.cancel()
    try:
        await vector_db_task
    except asyncio.CancelledError:
        pass

    await pubsub.unsubscribe("service.ready")
    await pubsub.aclose()
    await r.aclose()

    
@pytest.mark.asyncio
async def test_upload_embedding():
    message_payload = {
        "data": json.dumps({
            "image_id": "test-image-123",
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5]
        })
    }

    # Should complete without raising
    await vector_db.upload_embedding(message_payload)


@pytest.mark.asyncio
async def test_query_similar_images():
    r = Redis(host='localhost', port=6379, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("query.embedding_results")

    # Wait for subscription confirmation
    for _ in range(10):
        msg = await pubsub.get_message(timeout=1)
        if msg and msg["type"] == "subscribe":
            break

    message_payload = {
        "data": json.dumps({
            "tag": "sunset",
            "event_id": "test-event-456"
        })
    }

    handle_task = asyncio.create_task(vector_db.query_similar_images(message_payload))
    await asyncio.sleep(0.1)

    if handle_task.done() and handle_task.exception():
        raise handle_task.exception()

    # Poll for published result
    message = None
    for _ in range(10):
        message = await pubsub.get_message(timeout=2)
        if message and message["type"] == "message":
            break

    assert message is not None, "Did not receive any message on query.embedding_results channel"

    data = json.loads(message["data"])
    assert data["event_id"] == "test-event-456"
    assert "similar_image_ids" in data
    assert isinstance(data["similar_image_ids"], list)
    assert len(data["similar_image_ids"]) > 0

    # Cleanup
    handle_task.cancel()
    try:
        await handle_task
    except asyncio.CancelledError:
        pass

    await pubsub.unsubscribe("query.embedding_results")
    await pubsub.aclose()
    await r.aclose()