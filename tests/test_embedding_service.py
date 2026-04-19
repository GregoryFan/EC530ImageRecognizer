import asyncio
import base64
import json
import pytest
from redis.asyncio import Redis
import embedding_service
from unittest.mock import AsyncMock, patch, MagicMock

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

    embed_task = asyncio.create_task(embedding_service.start())

    message = None
    while message is None or message["type"] != "message":
        message = await pubsub.get_message(timeout=5)  

    assert message is not None, "Did not receive any message on service.ready channel"
    assert message["type"] == "message", f"Expected message type 'message', got {message['type']}"
    assert message["data"] == "embedding_service", f"Expected data 'embedding_service', got {message['data']}"

    #cleanup
    embed_task.cancel()
    try:
        await embed_task
    except asyncio.CancelledError:
        pass

    await pubsub.unsubscribe("service.ready")
    await pubsub.aclose()
    await r.aclose()



@pytest.mark.asyncio
async def test_generate_embedding_publishes_response():
    message = {
        "data": json.dumps({
            "image_id": "img_123",
            "event_id": "evt_456",
            "inferences": [
                {"label": "cat", "vertices": [[0, 0], [1, 1]]},
                {"label": "dog", "vertices": [[2, 2], [3, 3]]},
            ]
        })
    }
    mock_redis = AsyncMock()
    with patch("embedding_service.r", mock_redis):
        await embedding_service.generate_embedding(message)
    assert mock_redis.publish.call_count == 2
    for call in mock_redis.publish.call_args_list:
        channel, payload = call.args
        assert channel == "image.embedding_results"
        result = json.loads(payload)
        assert result["event_id"] == "evt_456"
        assert result["image_id"] == "img_123"
        assert "embedding" in result