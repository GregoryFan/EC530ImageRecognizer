import base64
import json
import asyncio
from redis.asyncio import Redis
from motor.motor_asyncio import AsyncIOMotorClient

r = None
mongo_client = None
images_collection = None
pubsub_upload = None
pubsub_queries = None

async def init():
    global r, mongo_client, images_collection, pubsub_upload, pubsub_queries
    r = Redis(host='localhost', port=6379, decode_responses=True)
    mongo_client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = mongo_client["image_db"]
    images_collection = db["images"]
    pubsub_upload = r.pubsub()
    pubsub_queries = r.pubsub()

async def start():
    await init()  # ← call init here instead of module level
    await pubsub_upload.subscribe("image.inference_results")
    print("[db_service] Listening on image.inference_results")
    await pubsub_queries.subscribe("query.embedding_results")
    print("[db_service] Listening on query.embedding_results")
    await r.sadd("services_ready", "db_service")
    await r.publish("service.ready", "db_service")
    embed_task = asyncio.create_task(listen_uploads())
    query_task = asyncio.create_task(listen_queries())
    try:
        await asyncio.gather(embed_task, query_task)
    except asyncio.CancelledError:
        print("[db_service] Shutting down listener...")
    finally:
        embed_task.cancel()
        query_task.cancel()
        try:
            await asyncio.gather(embed_task, query_task)
        except asyncio.CancelledError:
            pass
        await r.srem("services_ready", "db_service")
        await pubsub_upload.unsubscribe("image.inference_results")
        await pubsub_queries.unsubscribe("query.embedding_results")
        await pubsub_upload.aclose()
        await pubsub_queries.aclose()
        await r.aclose()

async def listen_uploads():
    async for message in pubsub_upload.listen():
        if message["type"] == "message":
            await upload_image(message)

async def listen_queries():
    async for message in pubsub_queries.listen():
        if message["type"] == "message":
            await query_image(message)

async def upload_image(message):
    json_data = json.loads(message["data"])
    image_id = json_data["image_id"]
    image_data = json_data["image_data"]
    inferences = json_data["inferences"]
    print(f"[db_service] Received image data for image: {image_id}")
    await images_collection.update_one(
        {"image_id": image_id},
        {"$set": {
            "image_id": image_id,
            "image_data": image_data,
            "inferences": inferences
        }},
        upsert=True
    )
    print(f"[db_service] Stored image {image_id} in MongoDB")

async def query_image(message):
    query_data = json.loads(message["data"])
    similar_image_ids = query_data["similar_image_ids"]
    event_id = query_data["event_id"]
    print(f"[db_service] Received query for similar image IDs: {similar_image_ids}")
    cursor = images_collection.find(
        {"image_id": {"$in": similar_image_ids}},
        {"image_data": 1, "image_id": 1, "_id": 0}
    )
    images = []
    async for doc in cursor:
        images.append(doc["image_data"])
    await r.publish(
        "query.results",
        json.dumps({
            "event_id": event_id,
            "image_data": images
        })
    )