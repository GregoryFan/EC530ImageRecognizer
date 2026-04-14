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

    await pubsub.unsubscribe("service.ready")
    await pubsub.aclose()
    await r.aclose()

@pytest.mark.asyncio
async def test_wait_for_services():
    
    r = Redis(host='localhost', port=6379, decode_responses=True)
    expected_services = {"test", "test_2"}

    main.await_for_services(r, expected_services)

    await r.sadd("services.ready", "test")

    #Check that the function is still waiting for the second service
    assert not r.sismember("services.ready", "test_2"), "Function should still be waiting for test_2 to be ready"
    await r.sadd("services.ready", "test_2")

    #Check that the function has now detected that both services are ready
    assert r.sismember("services.ready", "test_2"), "Function should have detected that test_2 is ready"

    #cleanup
    await r.srem("services.ready", "test")
    await r.srem("services.ready", "test_2")
    await r.aclose()
    

@pytest.mark.asyncio
async def test_handle_queried_images():
    assert True