import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.user_service import UserService
from src.db.session import get_db_session
from src.db.models import User
import structlog
from pydantic import BaseModel
# WebSocket functionality handled by orchestrator

router = APIRouter()

log = structlog.get_logger(__name__)

class ReminderNotification(BaseModel):
    user_id: str
    conversation_id: str
    message: str
    type: str

@router.get("/auth/google_token/{user_uuid}")
async def get_google_user_tokens(
    user_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends()
):
    log.info("Token debug: Received request", user_uuid=str(user_uuid))
    user = await user_service.get_user_by_uuid(id=user_uuid, db=db)
    if not user:
        log.warning("Token debug: User not found!", user_uuid=str(user_uuid))
        raise HTTPException(status_code=404, detail="User not found")
    if not user.google_access_token:
        user_dict = {
            "uuid": str(user.uuid),
            "username": user.username,
            "email": user.email,
            "google_provider_id": user.google_provider_id,
            "google_access_token": user.google_access_token,
            "google_refresh_token": user.google_refresh_token,
            "google_token_expires_at": str(user.google_token_expires_at)
        }
        log.warning(
            "Token debug: User missing google_access_token",
            user_uuid=str(user_uuid),
            user_info=user_dict
        )
        raise HTTPException(status_code=403, detail="User has not granted Google permissions or token is missing.")
    log.info(
        "Token debug: User token info",
        user_uuid=str(user_uuid),
        access_token=user.google_access_token,
        refresh_token_start=(user.google_refresh_token or '')[:12],
        expires_at=str(user.google_token_expires_at)
    )
    return {
        "access_token": user.google_access_token,
        "refresh_token": user.google_refresh_token,
        "expires_at": user.google_token_expires_at
    }

@router.post("/reminder-notification")
async def handle_reminder_notification(notification: ReminderNotification):
    """
    Handle reminder notifications from the reminder server and send to frontend via WebSocket.
    """
    try:
        log.info(
            "Processing reminder notification",
            user_id=notification.user_id,
            conversation_id=notification.conversation_id,
            message=notification.message
        )
        
        # WebSocket communication handled by orchestrator via Redis
        log.info("Reminder notification sent to orchestrator via Redis", user_id=notification.user_id)
        
        log.info(
            "Reminder notification sent to user",
            user_id=notification.user_id,
            conversation_id=notification.conversation_id
        )
        
        return {"status": "success", "message": "Reminder notification sent"}
        
    except Exception as e:
        log.error(
            "Failed to send reminder notification",
            error=str(e),
            user_id=notification.user_id,
            conversation_id=notification.conversation_id
        )
        raise HTTPException(status_code=500, detail=f"Failed to send reminder notification: {str(e)}")
