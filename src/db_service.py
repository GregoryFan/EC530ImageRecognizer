import base64
import json
import asyncio
from redis.asyncio import Redis
#Responsible for calling for images and embeddings from the database,
# and for inserting new images and embeddings into the database.

#Listens for the inference system to publish new embeddings, and stores them in the database.
#Listens for the vector database to query for similar images, and retrieves the relevant embeddings from the 
# database to return the results.

r = Redis(host='localhost', port=6379, decode_responses=True)
pubsub_upload = r.pubsub()
pubsub_queries = r.pubsub()

#Gets service ready to listen
async def start():
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
        print("[vector_db] Shutting down listener...")
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

        await pubsub_upload.close()
        await pubsub_queries.close()
        await r.aclose()

#Listen loop
async def listen_uploads():
    async for message in pubsub_upload.listen():
        if message["type"] == "message":
            await upload_image(message)
#Listen loop
async def listen_queries():
    async for message in pubsub_queries.listen():
        if message["type"] == "message":
            await query_image(message)


async def upload_image(message):
    json_data = json.loads(message["data"])
    image_id = json_data["image_id"]
    image_data = json_data["image_data"]
    
    print(f"[db_service] Received image data for image: {image_id}")

    # Code to upload the image data to the database

async def query_image(message):
    query_data = json.loads(message["data"])
    similar_image_ids = query_data["similar_image_ids"]

    print(f"[db_service] Received query for similar image IDs: {similar_image_ids}")

    #pretend i got the images from the db
    #TEST CODE
    with open("test.png", "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")
            
    images = [image_data]
    # Code to query the database given image ID 
    
    await r.publish(
        "query.results",
        json.dumps({
            "image_data": images
        })  
    )