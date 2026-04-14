import main
import asyncio
from redis.asyncio import Redis
import pytest



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

    cli_task = asyncio.create_task(main.start())

    message = None
    while message is None or message["type"] != "message":
        message = await pubsub.get_message(timeout=5)  

    assert message is not None, "Did not receive any message on service.ready channel"
    assert message["type"] == "message", f"Expected message type 'message', got {message['type']}"
    assert message["data"] == "cli_service", f"Expected data 'cli_service', got {message['data']}"

    #cleanup
    cli_task.cancel()
    try:
        await cli_task
    except asyncio.CancelledError:
        pass

    pubsub.unsubscribe("service.ready")
    await pubsub.close()
    await r.close()


    

@pytest.mark.asyncio
async def test_handle_queried_images():
    assert True