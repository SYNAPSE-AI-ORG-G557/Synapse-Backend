# src/main.py

import asyncio
import json
import uuid
import sys
import os
from contextlib import asynccontextmanager

# Add the parent directory to Python path for Railway deployment
# This allows importing 'src' as a top-level module
parent_dir = os.path.join(os.path.dirname(__file__), '..')
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Also add the src directory directly as a fallback
src_dir = os.path.join(parent_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Debug: Print the current working directory and Python path
print(f"Current working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")
print(f"Parent directory: {parent_dir}")
print(f"Src directory: {src_dir}")
print(f"Directory contents: {os.listdir(parent_dir) if os.path.exists(parent_dir) else 'Parent dir not found'}")
print(f"Src directory contents: {os.listdir(src_dir) if os.path.exists(src_dir) else 'Src dir not found'}")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware 
from starlette_prometheus import PrometheusMiddleware, metrics
import structlog

# Try to import with better error handling
try:
    from src.core.config import settings
    print("✅ Successfully imported src.core.config")
except ImportError as e:
    print(f"❌ Failed to import src.core.config: {e}")
    print("Attempting alternative import methods...")
    
    # Try importing from the absolute path
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("config", os.path.join(src_dir, "core", "config.py"))
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        settings = config_module.settings
        print("✅ Successfully imported config using importlib")
    except Exception as e2:
        print(f"❌ Alternative import also failed: {e2}")
        # Create a minimal settings object as fallback
        class MinimalSettings:
            def __init__(self):
                self.DEBUG = True
                self.DATABASE_DSN = "sqlite:///./test.db"
        settings = MinimalSettings()
        print("⚠️ Using minimal settings as fallback")
# Try to import other modules with error handling
try:
    from src.api.endpoints import processing, websockets, auth, users, conversation
    print("✅ Successfully imported API endpoints")
except ImportError as e:
    print(f"❌ Failed to import API endpoints: {e}")
    # Create minimal router objects
    class MinimalRouter:
        def __init__(self):
            pass
    processing = MinimalRouter()
    websockets = MinimalRouter()
    auth = MinimalRouter()
    users = MinimalRouter()
    conversation = MinimalRouter()

try:
    from src.core.redis_client import redis_client
    print("✅ Successfully imported Redis client")
except ImportError as e:
    print(f"❌ Failed to import Redis client: {e}")
    redis_client = None

try:
    from src.websockets.manager import connection_manager
    print("✅ Successfully imported WebSocket manager")
except ImportError as e:
    print(f"❌ Failed to import WebSocket manager: {e}")
    connection_manager = None

try:
    from src.core.logging_config import setup_logging
    print("✅ Successfully imported logging config")
except ImportError as e:
    print(f"❌ Failed to import logging config: {e}")
    def setup_logging():
        pass

try:
    from src.services.real.vector_store_service import RealVectorStoreService
    print("✅ Successfully imported vector store service")
except ImportError as e:
    print(f"❌ Failed to import vector store service: {e}")
    class RealVectorStoreService:
        def __init__(self):
            pass


# ----------------------------
# Logging Setup
# ----------------------------
setup_logging()
log = structlog.get_logger("app.main")


# ----------------------------
# Redis Pub/Sub Listener
# ----------------------------
async def redis_pubsub_listener():
    """Listens to 'job-updates' and forwards messages to WebSocket clients."""
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
# Lifespan Context for Startup/Shutdown
# ----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    log.info("Application startup")
    
    # Start background Redis listener
    listener_task = asyncio.create_task(redis_pubsub_listener())
    
    # Initialize the Qdrant collection on startup
    vector_store = RealVectorStoreService()
    try:
        log.info("Initializing Qdrant vector store...")
        await vector_store.initialize_store()
        log.info("Qdrant vector store initialized successfully.")
    except Exception as e:
        log.error("Failed to initialize Qdrant vector store", exc_info=e)
    
    try:
        yield
    finally:
        log.info("Application shutdown")
        listener_task.cancel()
        await redis_client.aclose()
        await vector_store.close()


# ----------------------------
# FastAPI App Initialization
# ----------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# ----------------------------
# Middleware Configuration
# ----------------------------

# CORS Middleware should be one of the first
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4173", # Your frontend dev server
        "http://localhost:3000", # Common alternative dev port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY) 
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", metrics)


@app.middleware("http")
async def add_context_to_logs(request: Request, call_next):
    """Adds a unique request ID to every log message for traceability."""
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
app.include_router(conversation.router, prefix=settings.API_V1_STR, tags=["Conversations"])
app.include_router(websockets.router)

# ----------------------------
# Root Endpoint
# ----------------------------
@app.get("/")
def read_root():
    """Root endpoint to confirm the API is running."""
    return {"message": f"Welcome to the {settings.PROJECT_NAME}!"}