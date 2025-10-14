# src/main.py

import asyncio
import json
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette_prometheus import PrometheusMiddleware, metrics
import structlog

from src.core.config import settings
from src.api.endpoints import processing, auth, users, conversation, automation
from src.core.redis_client import redis_client
# WebSocket functionality handled by orchestrator
from src.core.logging_config import setup_logging
# Import for the lifespan function
from src.services.real.vector_store_service import RealVectorStoreService
# from src.api.endpoints import ocr  # OCR moved to GPU workers
# from src.api.endpoints import automation  # Automation moved to unified Jarvis server
from src.api.endpoints import internal
from src.api.endpoints import memory
from src.api.endpoints import your_space, your_space_enhanced, google_sheets, google_drive_enhanced
from src.api.endpoints import tools
from src.api.endpoints import shell
from src.api.endpoints import google_drive
from src.api.endpoints import terminal
from src.api.endpoints import response_formatter
from src.api.endpoints import system_health
from src.api.endpoints import browser_proxy


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
                    # WebSocket communication handled by orchestrator via Redis
                    log.info("Message forwarded to orchestrator via Redis", client_id=client_id, job_id=job_id)
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
# WebSocket functionality handled by orchestrator
app.include_router(conversation.public_router, prefix=settings.API_V1_STR, tags=["Public"])
# app.include_router(ocr.router, prefix="/api/v1/ocr", tags=["OCR"])  # OCR moved to GPU workers

# ✨ --- THE FIX --- ✨
# Automation router moved to unified Jarvis server
# app.include_router(automation.router, prefix=settings.API_V1_STR, tags=["Automation"])
app.include_router(automation.router, prefix=settings.API_V1_STR, tags=["Automation"])
app.include_router(internal.router, prefix="/api/v1/internal", tags=["internal"])
app.include_router(memory.router, prefix=f"{settings.API_V1_STR}/memory", tags=["Memory"])
app.include_router(your_space.router, prefix=f"{settings.API_V1_STR}/your-space", tags=["Your Space"])
app.include_router(your_space_enhanced.router, prefix=f"{settings.API_V1_STR}/your-space", tags=["Your Space Enhanced"])
app.include_router(tools.router, prefix=f"{settings.API_V1_STR}", tags=["Tools"])
app.include_router(shell.router, prefix=f"{settings.API_V1_STR}/shell", tags=["Shell"])
app.include_router(google_drive.router, prefix=f"{settings.API_V1_STR}/google-drive", tags=["Google Drive"])
app.include_router(google_drive_enhanced.router, prefix=f"{settings.API_V1_STR}/google-drive", tags=["Google Drive Enhanced"])
app.include_router(google_sheets.router, prefix=f"{settings.API_V1_STR}/google-sheets", tags=["Google Sheets"])
app.include_router(terminal.router, prefix=f"{settings.API_V1_STR}", tags=["Terminal"])
app.include_router(response_formatter.router, prefix=f"{settings.API_V1_STR}", tags=["Response Formatter"])
app.include_router(system_health.router, prefix=f"{settings.API_V1_STR}", tags=["System Health"])
app.include_router(browser_proxy.router, prefix=f"{settings.API_V1_STR}/browser", tags=["Browser Proxy"])


# ----------------------------
# Root Endpoint
# ----------------------------
@app.get("/")
def read_root():
    """Root endpoint to confirm the API is running."""
    return {"message": f"Welcome to the {settings.PROJECT_NAME}!"}