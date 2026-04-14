import json
import asyncio
from redis.asyncio import Redis
#Generates inferences, which is defined by the following:

#An inference is a boundary where an object is detected.
#[vertices, defined as (x,y) coordinates] and label, which is a string.
#An image may have multiple inferences.

#Implementation is not done in this project but estimated with dummy code.

#Listens for the Upload Service when it sends image data over.
#Publishes the inference data as the following, in JSON format.
#{
#   "image_id": "unique_image_identifier",
#   "image": image_data,  # This could be a base64 string or a file path
#    "inferences": [
#        {
#            "label": "object_label",
#            "vertices": [(x1, y1), (x2, y2),
#                         (x3, y3), (x4, y4)]
#        },
#        ...
#    ]
#}

#Redis services
r = Redis(host='localhost', port=6379, decode_responses=True)
pubsub = r.pubsub()

#Gets service ready to listen
async def start():
    await pubsub.subscribe("image.inferrences")
    print("[inference_service] Listening on image.inferrences")

    await r.sadd("services_ready", "inference_service")
    await r.publish("service.ready", "inference_service")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await generate_inferences(message)
    except asyncio.CancelledError:
        print("[inference_service] Shutting down listener...")
    finally:
        await r.srem("services_ready", "inference_service")
        await pubsub.unsubscribe("image.inferences")
        await pubsub.close()
        await r.close()

async def generate_inferences(message):
    data = json.loads(message["data"])
    image_id = data["image_id"]
    image_data = data["image_data"]

    print(f"[inference_service] Received image for inference: {image_id}")

    #dummy inferences, no idea how real they are gonna be given.
    inferences = [
        {
            "label": "cat",
            "vertices": [(10, 10), (100, 10), (100, 100), (10, 100)]
        },
        {
            "label": "dog",
            "vertices": [(150, 150), (250, 150), (250, 250), (150, 250)]
        }
    ]

    await r.publish(
        "image.inference_results",
        json.dumps({
            "image_id": image_id,
            "image_data": image_data,
            "inferences": inferences
        })
    )

