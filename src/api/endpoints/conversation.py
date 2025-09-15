import uuid
from typing import Annotated

# 👇 The typo is fixed here
from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.services.real.db_service import RealDatabaseService
from src.services.real.redis_service import RealRedisService
from src.schemas.conversation import MessageCreate
from src.schemas.job import JobCreate, JobCreated
from src.db.database import get_db_session
from src.core.celery_app import celery_app
from src.core.dependencies import get_current_active_user
from src.core.redis_client import redis_client
from src.db.models import User
from src.crud import conversation_crud

router = APIRouter()

def get_redis() -> redis.Redis:
    return redis_client

def get_redis_service(client: Annotated[redis.Redis, Depends(get_redis)]) -> RealRedisService:
    return RealRedisService(client)

@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=JobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Post a message and trigger AI response"
)
async def post_message(
    request: Request,
    conversation_id: uuid.UUID,
    message_in: MessageCreate,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    redis_service: Annotated[RealRedisService, Depends(get_redis_service)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Orchestrates a full conversational turn: saves the message, creates a
    ProcessingJob, and dispatches it to the workers.
    """
    db_service = RealDatabaseService(db_session)

    await conversation_crud.conversation.get_or_create(
        db=db_session,
        user_id=current_user.uuid,
        conversation_id=conversation_id
    )
    
    await db_service.add_chat_message(
        user_id=current_user.uuid,
        conversation_id=conversation_id,
        role="user",
        content=message_in.content
    )
    await redis_service.add_message_to_history(
        conversation_id=conversation_id,
        message={"role": "user", "content": message_in.content}
    )

    job_id = uuid.uuid4()
    job_payload = JobCreate(
        user_id=current_user.uuid,
        conversation_id=conversation_id,
        input_type="text",
        input_data=message_in.content
    )

    await db_service.create_job(job_id=job_id, job_data=job_payload)

    celery_app.send_task(
        "route_input_task",
        args=[str(job_id), str(current_user.uuid), job_payload.model_dump(), str(conversation_id)],
        queue="cpu_light"
    )

    SUMMARIZATION_THRESHOLD = 10
    message_count = await db_service.get_conversation_message_count(conversation_id)
    if message_count > 0 and message_count % SUMMARIZATION_THRESHOLD == 0:
        celery_app.send_task(
            "summarize_conversation_task",
            args=[str(conversation_id), str(current_user.uuid)],
            queue='cpu_heavy'
        )

    status_url = str(request.url_for("get_job_status", job_id=job_id))
    return JobCreated(job_id=job_id, status_url=status_url)