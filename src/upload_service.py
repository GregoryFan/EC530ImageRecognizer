import json
import asyncio
from redis.asyncio import Redis
import base64
import os
import uuid

r = Redis(host='localhost', port=6379, decode_responses=True)
pubsub = r.pubsub()

#Uploads images to the database and calls for relevent embeddings to be generated.

#Gets service ready to listen
async def start():
    await pubsub.subscribe("image.uploads")
    print("[upload_service] Listening on image_uploads")

    await r.sadd("services_ready", "upload_service")
    await r.publish("service.ready", "upload_service")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await handle_uploaded_image(message)
    except asyncio.CancelledError:
        print("[upload_service] Shutting down listener...")
    finally:
        await r.srem("services_ready", "upload_service")
        await pubsub.unsubscribe("image_uploads")
        await pubsub.close()
        await r.close()

    
#Listens for the CLI when it receives an image upload
#Will publish the image data for listeners to process.
#Goals:
#Take image path and attempts to get the file and convert it to a base64 string, 
# then publish that string for listeners to process.
async def handle_uploaded_image(message):
    data = json.loads(message["data"])
    image_path = data["image_path"]

    print(f"[upload_service] Received: {image_path}")

    #Get the file, if possible
    try:
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        print(f"[upload_service] Error reading file: {e}")
        return

    #Sends this over to the inference service.
    await r.publish(
        "image.inferrences",
        json.dumps({
            "image_id": str(uuid.uuid4()),  
            "image_data": image_data
        })
    )