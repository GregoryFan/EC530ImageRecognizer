import base64
import json
import upload_service
import inference_service
import embedding_service
import vector_db
import db_service
import asyncio
from redis.asyncio import Redis
import subprocess

#CLI Portion of the project
#Asks the user either to import an image or query for images.
#Uses a socket connection to host everything.

#Listens for the database when querying happens to pass the image.

r = Redis(host='localhost', port=6379, decode_responses=True)
pubsub = r.pubsub()

#Gets service ready to listen
async def start():
    await pubsub.subscribe("query.results")
    print("[cli] Listening on query.results")

    await r.sadd("services_ready", "cli_service")
    await r.publish("service.ready", "cli_service")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await handle_queried_images(message)
    except asyncio.CancelledError:
        print("[cli] Shutting down listener...")
    finally:
        await r.srem("services_ready", "cli_service")
        await pubsub.unsubscribe("query.results")
        await pubsub.aclose()
        await r.aclose()

#async input function
async def cli():
    print("\nStarting Services..\n")
    expected_services = {
        "upload_service",
        "inference_service",
        "embedding_service",
        "vector_db",
        "db_service",
        "cli_service"
    }
    await wait_for_services(r, expected_services)
    print("\nServices started.\n")

    
    while True:
        user_input = await asyncio.get_event_loop().run_in_executor(
            None, input, "\nUse the service through the commands:\n'upload [image_path]' to upload an image\n'query [tag]' to query for images\n'quit' to exit:\n\nCommand: "
        )
        print() #New line for formatting.
        if user_input.startswith("upload"):
            image_path = user_input.split(" ")[1]
            await r.publish(
                "image.uploads",
                json.dumps({"image_path": image_path})
            )
        elif user_input.startswith("query"):
            tag = user_input.split(" ")[1]
            await r.publish(
                "query.images",
                json.dumps({"tag": tag})
            )
        elif user_input == "quit":
            print("Exiting.")
            await r.aclose()
            break
        else:
            print("Invalid command. Please try again.")
        
        await asyncio.sleep(0.5) #let services run a bit

async def wait_for_services(r, expected_services):
    pubsub = r.pubsub()
    await pubsub.subscribe("service.ready")

    ready = set()

    while True:
        message = await pubsub.get_message(
            ignore_subscribe_messages=True,
            timeout=1.0
        )

        if message:
            service_name = message["data"]
            ready.add(service_name)

            if ready == expected_services:
                break

        await asyncio.sleep(0.1)

    await pubsub.unsubscribe("service.ready")
    await pubsub.aclose()

async def handle_queried_images(message):
    data = json.loads(message["data"])
    image_data_list = data["image_data"]
    print(f"[cli] Received {len(image_data_list)} images from query results.")

    for idx, image_data in enumerate(image_data_list):
        image_bytes = base64.b64decode(image_data)
        path = f"queried_image_{idx}.png"
        with open(path, "wb") as f:
            f.write(image_bytes)
        subprocess.Popen(["open", path])

async def main():
    upload_task = asyncio.create_task(upload_service.start())
    inference_task = asyncio.create_task(inference_service.start())
    embedding_task = asyncio.create_task(embedding_service.start())
    vector_db_task = asyncio.create_task(vector_db.start())
    db_service_task = asyncio.create_task(db_service.start())
    cli_service_task = asyncio.create_task(start())
    cli_task = asyncio.create_task(cli())

    await cli_task  # wait until user quits

    print("Shutting down...")

    upload_task.cancel()
    inference_task.cancel()
    embedding_task.cancel()
    vector_db_task.cancel()
    db_service_task.cancel()
    cli_service_task.cancel()
    #shut down everything else
    try:
        await upload_task
        await inference_task
        await embedding_task
        await vector_db_task
        await db_service_task
        await cli_service_task
    except asyncio.CancelledError:
        pass
    print("Successfully shut down.\n")

if __name__ == "__main__":
    asyncio.run(main())