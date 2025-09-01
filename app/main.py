import asyncio
import json
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware # ++ ADDED ++
from starlette_prometheus import PrometheusMiddleware, metrics

from src.core.config import settings
from src.api.endpoints import processing, websockets, auth, users
from src.core.redis_client import redis_client
from src.websockets.manager import connection_manager
from src.core.logging_config import setup_logging
import structlog

# ----------------------------
# Logging Setup
# ----------------------------
setup_logging()
log = structlog.get_logger()


# ----------------------------
# Redis Pub/Sub Listener
# ----------------------------
async def redis_pubsub_listener():
    """
    Background task listening to the 'job-updates' Redis Pub/Sub channel
    and forwarding messages to the appropriate WebSocket clients.
    """
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("job-updates")
    log.info("Subscribed to 'job-updates' channel")

    while True:
        try:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=None)
            if message and message.get("data"):
                data = json.loads(message["data"])
                client_id = data.get("user_id")
                job_id = data.get("job_id")

                if client_id:
                    await connection_manager.send_personal_message(data, client_id)
                    log.info("Sent message to client", client_id=client_id, job_id=job_id)
                else:
                    log.warning("No client_id found in message", job_id=job_id)
        except Exception as e:
            log.error("Error in Redis listener", error=str(e))
            await asyncio.sleep(1)


# ----------------------------
# Lifespan Context
# ----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Application startup")
    # Start background Redis listener
    listener_task = asyncio.create_task(redis_pubsub_listener())
    try:
        yield
    finally:
        log.info("Application shutdown")
        listener_task.cancel()
        await redis_client.aclose()


# ----------------------------
# FastAPI App Initialization
# ----------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# ++ ADDED: Session Middleware for Google OAuth state management ++
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)


# ----------------------------
# Prometheus Metrics
# ----------------------------
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", metrics)

# ----------------------------
# Middleware: Request Context for Logging
# ----------------------------
@app.middleware("http")
async def add_context_to_logs(request: Request, call_next):
    request_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        client_ip=request.client.host
    )
    response = await call_next(request)
    structlog.contextvars.clear_contextvars()
    return response
    
# ----------------------------
# API Routers
# ----------------------------
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["Authentication"]) 
app.include_router(processing.router, prefix=settings.API_V1_STR, tags=["Processing"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])
app.include_router(websockets.router)

# ----------------------------
# Root Endpoint
# ----------------------------
@app.get("/")
def read_root():
    """Root endpoint to confirm the API is running."""
    return {"message": f"Welcome to the {settings.PROJECT_NAME}!"}