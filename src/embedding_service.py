import json
import asyncio
from redis.asyncio import Redis

#Embedding Service for generating image embeddings

#Listens for image inference data, and generates embeddings for the image.
#Publishes the embedding data as the following, in JSON format.
#{
#   "image_id": "unique_image_identifier",
#   "embedding": [0.1, 0.2, 0.3, ...]  # This is a list of numbers representing the embedding
#}

#redis services
r = Redis(host='localhost', port=6379, decode_responses=True)
pubsub = r.pubsub()

#Gets service ready to listen
async def start():
    await pubsub.subscribe("image.inference_results")
    print("[embedding_service] Listening on image.inference_results")

    await r.sadd("services_ready", "embedding_service")
    await r.publish("service.ready", "embedding_service")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await generate_embedding(message)
    except asyncio.CancelledError:
        print("[embedding_service] Shutting down listener...")
    finally:
        await r.srem("services_ready", "embedding_service")
        await pubsub.unsubscribe("image.inference_results")
        await pubsub.close()
        await r.close()

async def generate_embedding(message):
    data = json.loads(message["data"])
    image_id = data["image_id"]
    inferences = data["inferences"]
    event_id = data["event_id"]

    print(f"[embedding_service] Received inferences for image: {image_id}")
    
    embeddings = []
    for inference in inferences:
        #Unused i guess
        label = inference["label"]
        vertices = inference["vertices"]

        #embeddings should be generated based on vertices and label, but what do i know
        embedding = [0.1, 0.2, 0.3]

        #For Testing
        if image_id == "d-o-g":
            embedding = [1, 1, 1]
        elif image_id == "c-a-t":
            embedding = [0, 0, 0]
        
        embeddings.append(embedding)

    for embedding in embeddings:
        await r.publish(
            "image.embedding_results",
            json.dumps({
                "event_id": event_id,
                "image_id": image_id,
                "embedding": embedding,
                "inference": inference
            })
        )