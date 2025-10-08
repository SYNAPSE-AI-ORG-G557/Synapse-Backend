# src/api/endpoints/conversation.py

import uuid
import io
import csv
import base64
from typing import Annotated, List, Union, Optional
import logging

from fastapi import (
    APIRouter,
    Depends,
    status,
    Request,
    HTTPException,
    Query,
    UploadFile,
    File,
    Form
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import redis.asyncio as redis

from src.schemas.conversation import (
    MessageCreate,
    MessagePublic,
    ConversationWithMessages,
    ConversationUpdate,
    ConversationShareInfo,
)
# ✅ ADDED: Import new schemas for job handling
from src.schemas.job import JobCreate, ClarificationResponse
from src.db.database import get_db_session
from src.core.celery_app import celery_app
from src.core.dependencies import get_current_active_user, get_user_from_token
from src.core.redis_client import redis_client
from src.db import models
from src.crud import conversation_crud
from src.services.real.db_service import RealDatabaseService
from src.services.real.redis_service import RealRedisService

log = logging.getLogger(__name__)

router = APIRouter()
public_router = APIRouter()


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------
def get_redis() -> redis.Redis:
    """Dependency to get the Redis client instance."""
    return redis_client


def get_redis_service(
    client: Annotated[redis.Redis, Depends(get_redis)]
) -> RealRedisService:
    """Dependency to get an instance of the Redis service."""
    return RealRedisService(client)


async def get_user_for_export(
    token: str = Query(None),
    current_user: models.User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
) -> models.User:
    """
    Authenticates a user for export operations.
    Prioritizes the 'token' query parameter, falling back to the standard
    HTTP-only cookie authentication.
    """
    if token:
        log.info("[DEBUG] Attempting authentication for export via URL token.")
        user = await get_user_from_token(token, db)
        if user:
            log.info(f"[DEBUG] Successfully authenticated user {user.uuid} via URL token.")
            return user
    
    log.info(f"[DEBUG] Falling back to standard cookie authentication for user {current_user.uuid}.")
    return current_user


# =============================================================================
# GET all conversations for the current user
# =============================================================================
@router.get(
    "/conversations/",
    response_model=List[ConversationWithMessages],
    summary="Get all conversations for the current user",
)
async def get_user_conversations(
    current_user: Annotated[models.User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Retrieve all conversations and their associated messages for the current user.
    """
    stmt = (
        select(models.Conversation)
        .where(models.Conversation.user_id == current_user.uuid)
        .options(selectinload(models.Conversation.messages))
        .order_by(models.Conversation.updated_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


# =============================================================================
# POST a new message and trigger AI response
# =============================================================================
@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessagePublic,
    status_code=status.HTTP_201_CREATED,
    summary="Post a message and trigger AI response",
)
async def post_message(
    request: Request,
    conversation_id: uuid.UUID,
    message_in: MessageCreate,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    redis_service: Annotated[RealRedisService, Depends(get_redis_service)],
    current_user: Annotated[models.User, Depends(get_current_active_user)],
):
    """
    Orchestrates a full conversational turn for TEXT messages:
    saves the message, creates a ProcessingJob, and dispatches it to workers.
    """
    db_service = RealDatabaseService(db_session)

    # Ensure the conversation exists
    await conversation_crud.conversation.get_or_create(
        db=db_session,
        user_id=current_user.uuid,
        conversation_id=conversation_id,
    )

    message_count_before_add = await db_service.get_conversation_message_count(conversation_id)
    created_message = await db_service.add_chat_message(
        user_id=current_user.uuid,
        conversation_id=conversation_id,
        role="user",
        content=message_in.content,
    )

    if message_count_before_add == 0:
        celery_app.send_task("generate_title_task", args=[str(conversation_id), message_in.content], queue="cpu_heavy")

    await redis_service.add_message_to_history(
        conversation_id=conversation_id, message={"role": "user", "content": message_in.content}
    )

    job_id = uuid.uuid4()
    job_payload = JobCreate(
        user_id=current_user.uuid, conversation_id=conversation_id,
        input_type="text", input_data=message_in.content,
        is_personalization_enabled=message_in.is_personalization_enabled,
    )
    await db_service.create_job(job_id=job_id, job_data=job_payload)

    celery_app.send_task("route_input_task",
        args=[str(job_id), str(current_user.uuid), job_payload.model_dump(), str(conversation_id), message_in.is_personalization_enabled],
        queue="cpu_light",
    )

    SUMMARIZATION_THRESHOLD = 10
    if (message_count_before_add + 1) % SUMMARIZATION_THRESHOLD == 0:
        celery_app.send_task("summarize_conversation_task", args=[str(conversation_id), str(current_user.uuid)], queue="cpu_heavy")

    return created_message


# =============================================================================
# POST a file (image/audio) to trigger OCR/STT
# =============================================================================
@router.post(
    "/conversations/{conversation_id}/upload",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload file for OCR/STT processing",
)
async def upload_and_process_file(
    conversation_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_active_user),
    db_session: AsyncSession = Depends(get_db_session),
):
    """
    Handles file uploads, determines the processing task (OCR or STT)
    based on MIME type, and dispatches the job to the appropriate worker queue.
    """
    db_service = RealDatabaseService(db_session)
    await conversation_crud.conversation.get_or_create(
        db=db_session, user_id=current_user.uuid, conversation_id=conversation_id
    )

    content_type = file.content_type
    task_name = None
    input_type = None

    if content_type.startswith("image/"):
        task_name = "perform_ocr_task"
        input_type = "image"
    elif content_type.startswith("audio/"):
        task_name = "perform_stt_task"
        input_type = "audio"
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    file_bytes = await file.read()
    encoded_data = base64.b64encode(file_bytes).decode("utf-8")

    job_id = uuid.uuid4()
    job_payload = JobCreate(
        user_id=current_user.uuid,
        conversation_id=conversation_id,
        input_type=input_type,
        input_data=f"Processing {content_type} file...",
    )
    await db_service.create_job(job_id=job_id, job_data=job_payload)

    celery_app.send_task(
        task_name,
        kwargs={
            'job_id': str(job_id),
            'user_id': str(current_user.uuid),
            'conversation_id': str(conversation_id),
            'image_data' if input_type == 'image' else 'audio_data': encoded_data
        },
        queue="gpu"
    )
    
    return {"status": "processing", "job_id": str(job_id), "conversation_id": str(conversation_id)}


# =============================================================================
# ✅ NEW: Endpoint for submitting clarification responses
# =============================================================================
@router.post(
    "/jobs/{job_id}/clarify",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a clarification response for a paused job",
)
async def handle_clarification(
    job_id: uuid.UUID,
    response: ClarificationResponse,
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Receives the user's response to a clarification request
    and resumes the corresponding job.
    """
    celery_app.send_task(
        "resume_with_clarification_task",
        kwargs={
            "job_id": str(job_id),
            "user_id": str(current_user.uuid),
            "user_response": response.user_response,
        },
        queue="cpu_light"
    )
    return {"status": "clarification received, resuming job"}


# =============================================================================
# PATCH to rename a conversation
# =============================================================================
@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationWithMessages,
    summary="Rename a conversation",
)
async def rename_conversation(
    conversation_id: uuid.UUID,
    conversation_in: ConversationUpdate,
    current_user: Annotated[models.User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Renames a conversation and returns the updated conversation with all messages.
    """
    stmt = (
        select(models.Conversation)
        .where(
            models.Conversation.uuid == conversation_id,
            models.Conversation.user_id == current_user.uuid,
        )
        .options(selectinload(models.Conversation.messages))
    )
    result = await session.execute(stmt)
    conversation = result.scalars().first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found...")

    conversation.title = conversation_in.title
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    
    _ = conversation.messages
    return conversation


# =============================================================================
# DELETE a conversation
# =============================================================================
@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: Annotated[models.User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Deletes a conversation and all of its associated messages.
    """
    stmt = select(models.Conversation).where(
        models.Conversation.uuid == conversation_id,
        models.Conversation.user_id == current_user.uuid,
    )
    result = await session.execute(stmt)
    conversation = result.scalars().first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found...")
    await session.delete(conversation)
    await session.commit()
    return None


# =============================================================================
# EXPORT a conversation (Markdown, CSV, or PDF)
# =============================================================================
@router.get(
    "/conversations/{conversation_id}/export",
    summary="Export a conversation",
)
async def export_conversation(
    conversation_id: uuid.UUID,
    current_user: Annotated[models.User, Depends(get_user_for_export)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    format: Union[str, None] = Query(default="md", enum=["md", "csv", "pdf"]),
):
    """
    Export a conversation to Markdown (.md), CSV (.csv), or PDF (.pdf).
    """
    log.info(f"[DEBUG] Export request for conv '{conversation_id}' by user '{current_user.uuid}' in format '{format}'.")
    
    stmt = (
        select(models.Conversation)
        .where(
            models.Conversation.uuid == conversation_id,
            models.Conversation.user_id == current_user.uuid,
        )
        .options(selectinload(models.Conversation.messages))
    )
    result = await session.execute(stmt)
    conversation = result.scalars().first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    file_name = f"{conversation.title.replace(' ', '_')}_{conversation.uuid}.{format}"
    headers = {"Content-Disposition": f'attachment; filename="{file_name}"'}

    if format == "md":
        content = f"# {conversation.title}\n\n"
        for msg in conversation.messages:
            content += f"**{msg.role.capitalize()}**:\n{msg.content}\n\n---\n\n"
        return StreamingResponse(io.BytesIO(content.encode()), media_type="text/markdown", headers=headers)

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["role", "content", "created_at"])
        for msg in conversation.messages:
            writer.writerow([msg.role, msg.content, msg.created_at.isoformat()])
        return StreamingResponse(io.BytesIO(output.getvalue().encode()), media_type="text/csv", headers=headers)

    if format == "pdf":
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
        except ImportError:
            raise HTTPException(status_code=501, detail="PDF generation library not installed.")
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = [Paragraph(conversation.title, styles["h1"])]
        for msg in conversation.messages:
            story.append(Spacer(1, 12))
            story.append(Paragraph(f"<b>{msg.role.capitalize()}</b>:", styles["h3"]))
            story.append(Paragraph(msg.content.replace("\n", "<br/>"), styles["BodyText"]))
        doc.build(story)
        buffer.seek(0)
        return StreamingResponse(buffer, media_type="application/pdf", headers=headers)

    raise HTTPException(status_code=400, detail="Invalid format specified.")


# =============================================================================
# Endpoints for Sharing Conversations
# =============================================================================
@router.post(
    "/conversations/{conversation_id}/share",
    response_model=ConversationShareInfo,
    summary="Make a conversation public and get its share link"
)
async def share_conversation(
    conversation_id: uuid.UUID,
    current_user: models.User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Generates a shareable link for a conversation by making it public.
    """
    stmt = select(models.Conversation).where(
        models.Conversation.uuid == conversation_id,
        models.Conversation.user_id == current_user.uuid,
    )
    result = await session.execute(stmt)
    conversation = result.scalars().first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    if not conversation.share_uuid:
        conversation.share_uuid = uuid.uuid4()
    
    conversation.is_public = True
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    
    return conversation

@router.delete(
    "/conversations/{conversation_id}/share",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Make a conversation private"
)
async def unshare_conversation(
    conversation_id: uuid.UUID,
    current_user: models.User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Revokes public access to a shared conversation.
    """
    stmt = select(models.Conversation).where(
        models.Conversation.uuid == conversation_id,
        models.Conversation.user_id == current_user.uuid,
    )
    result = await session.execute(stmt)
    conversation = result.scalars().first()
    if conversation:
        conversation.is_public = False
        session.add(conversation)
        await session.commit()
    return None

@public_router.get(
    "/public/conversations/{share_uuid}",
    response_model=ConversationWithMessages,
    summary="Get a publicly shared conversation",
)
async def get_shared_conversation(
    share_uuid: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Retrieves a conversation that has been made public via its share UUID.
    This endpoint does not require authentication.
    """
    stmt = (
        select(models.Conversation)
        .where(
            models.Conversation.share_uuid == share_uuid,
            models.Conversation.is_public == True,
        )
        .options(selectinload(models.Conversation.messages))
    )
    result = await session.execute(stmt)
    conversation = result.scalars().first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Shared conversation not found or is no longer public.")
    return conversation