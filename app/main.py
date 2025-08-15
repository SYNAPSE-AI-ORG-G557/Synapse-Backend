import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.core.config import settings
from src.api.endpoints import processing
from src.core.redis_client import redis_client
from src.websockets.manager import connection_manager


async def redis_pubsub_listener():
    """
    Background task listening to the 'job-updates' Redis Pub/Sub channel
    and forwarding messages to the appropriate WebSocket clients.
    """
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("job-updates")
    print("Subscribed to 'job-updates' channel. Listening for messages...")

    while True:
        try:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=None)
            if message:
                data = json.loads(message['data'])
                job_id = data.get("job_id")

                # Map job_id to a WebSocket client_id
                client_id_for_job = f"user_for_{job_id}"

                # Forward message to WebSocket client
                await connection_manager.send_personal_message(data, client_id_for_job)

        except Exception as e:
            print(f"Error in Redis listener: {e}")
            await asyncio.sleep(1)  # Prevent tight-loop on errors


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    """
    # Start Redis listener on app startup
    asyncio.create_task(redis_pubsub_listener())
    yield
    # Close Redis connection pool on shutdown
    await redis_client.aclose()


# --- Initialize FastAPI App ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# --- Include API Routers ---
app.include_router(processing.router, prefix=settings.API_V1_STR, tags=["Processing"])


@app.get("/")
def read_root():
    """Root endpoint to confirm the API is running."""
    return {"message": f"Welcome to the {settings.PROJECT_NAME}!"}
