import main
import asyncio
from redis.asyncio import Redis
import pytest

#r = Redis(host='localhost', port=6379, decode_responses=True)
#pubsub = r.pubsub()

@pytest.mark.asyncio
async def test_start():
    assert True

@pytest.mark.asyncio
async def test_wait_for_services():
    assert True

@pytest.mark.asyncio
async def test_handle_queried_images():
    assert True