# src/api/endpoints/memory.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.dependencies import get_db_session, get_current_active_user
from src.db import models
from src.core.celery_app import celery_app
import structlog

log = structlog.get_logger(__name__)

router = APIRouter()

@router.post("/store_memory", status_code=202, summary="Store a memory for the user")
async def store_memory(
    body: dict = Body(...),
    current_user: models.User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Accepts text content to be stored in the user's memory asynchronously.
    Dispatches a background task and returns immediately.
    """
    job_id = str(uuid.uuid4())
    log.info("Dispatching store_memory task.", job_id=job_id)

    # Handle missing fields gracefully with defaults
    conversation_id = body.get("conversation_id")
    content = body.get("content", body.get("text", ""))
    
    if not conversation_id:
        # Create a default conversation ID if none provided
        conversation_id = str(uuid.uuid4())
        log.info("No conversation_id provided, using default.", conversation_id=conversation_id)
    
    if not content:
        content = "Memory stored via API"
        log.info("No content provided, using default.", content=content)

    celery_app.send_task(
        "save_memory_task",
        kwargs={
            "job_id": job_id,
            "user_id": str(current_user.uuid),
            "conversation_id": str(conversation_id),
            "text_to_store": content,
        },
    )
    return {"job_id": job_id, "message": "Memory storage task accepted."}

@router.post("/retrieve_memory", status_code=202, summary="Retrieve memories for the user")
async def retrieve_memory(
    body: dict = Body(...),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Finds relevant memories based on a query using the main asynchronous pipeline.
    No waiting for sync results: fire-and-forget agentic route only.
    """
    job_id = str(uuid.uuid4())
    log.info("Dispatching memory retrieval via main agentic router.", job_id=job_id)

    # Handle missing fields gracefully with defaults
    conversation_id = body.get("conversation_id")
    query_text = body.get("query_text", body.get("text", ""))
    
    if not conversation_id:
        # Create a default conversation ID if none provided
        conversation_id = str(uuid.uuid4())
        log.info("No conversation_id provided, using default.", conversation_id=conversation_id)
    
    if not query_text:
        query_text = "general memory retrieval"
        log.info("No query_text provided, using default.", query_text=query_text)

    celery_app.send_task(
        "route_input_task",
        kwargs={
            "job_id": job_id,
            "user_id": str(current_user.uuid),
            "conversation_id": str(conversation_id),
            "text": query_text,
            "hard_route": "retrieve_info",
        },
    )

    return {"job_id": job_id, "message": "Memory retrieval task accepted."}
