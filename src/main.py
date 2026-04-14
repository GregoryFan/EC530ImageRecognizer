import json
import upload_service
import inference_service
import asyncio
from redis.asyncio import Redis

#CLI Portion of the project
#Asks the user either to import an image or query for images.
#Uses a socket connection to host everything.

#Listens for the database when querying happens to pass the image.

r = Redis(host='localhost', port=6379, decode_responses=True)

#async input function
async def cli():
    print("\nStarting Services..\n")
    expected_services = {
        "upload_service",
        "inference_service"
    }
    await wait_for_services(r, expected_services)
    print("\nServices started.\n")

    
    while True:
        user_input = await asyncio.get_event_loop().run_in_executor(
            None, input, "\nUse the service through the commands:\n'upload [image_path]' to upload an image\n'query [tag]' to query for images\n'quit' to exit:\n\n Command: "
        )
        print() #New line for formatting.
        if user_input.startswith("upload"):
            image_path = user_input.split(" ")[1]
            await r.publish(
                "image.uploads",
                json.dumps({"image_path": image_path})
            )
        elif user_input.startswith("query"):
            #TODO
            pass
        elif user_input == "quit":
            print("Exiting.")
            await r.aclose()
            break
        else:
            print("Invalid command. Please try again.")

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

async def main():
    upload_task = asyncio.create_task(upload_service.start())
    inference_task = asyncio.create_task(inference_service.start())
    cli_task = asyncio.create_task(cli())

    await cli_task  # wait until user quits

    print("Shutting down...")

    upload_task.cancel()
    inference_task.cancel()
    #shut down everything else
    try:
        await upload_task
        await inference_task
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    asyncio.run(main())