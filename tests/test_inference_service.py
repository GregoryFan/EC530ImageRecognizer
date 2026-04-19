import asyncio
import base64
import json
import pytest
from redis.asyncio import Redis
import inference_service
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

    infer_task = asyncio.create_task(inference_service.start())

    message = None
    while message is None or message["type"] != "message":
        message = await pubsub.get_message(timeout=5)  

    assert message is not None, "Did not receive any message on service.ready channel"
    assert message["type"] == "message", f"Expected message type 'message', got {message['type']}"
    assert message["data"] == "inference_service", f"Expected data 'inference_service', got {message['data']}"

    #cleanup
    infer_task.cancel()
    try:
        await infer_task
    except asyncio.CancelledError:
        pass

    await pubsub.unsubscribe("service.ready")
    await pubsub.aclose()
    await r.aclose()

@pytest.mark.asyncio
async def test_generate_inferences_publishes_response():
    message = {
        "data": json.dumps({
            "image_id": "img_123",
            "event_id": "evt_456",
            "image_data": "base64encodeddata"
        })
    }
    mock_redis = AsyncMock()
    with patch("inference_service.r", mock_redis):
        await inference_service.generate_inferences(message)
    mock_redis.publish.assert_called_once()
    channel, payload = mock_redis.publish.call_args.args
    assert channel == "image.inference_results"
    result = json.loads(payload)
    assert result["event_id"] == "evt_456"
    assert result["image_id"] == "img_123"
    assert result["image_data"] == "base64encodeddata"
    assert "inferences" in result