import uuid
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from datetime import datetime, timezone
from authlib.integrations.httpx_client import AsyncOAuth2Client
import structlog

from src.db.models import User
from src.core.config import settings
from src.db.database import get_db_session

log = structlog.get_logger(__name__)

class GoogleAuthService:
    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        self.db = db
        self.oauth_client = AsyncOAuth2Client(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            token_endpoint='https://oauth2.googleapis.com/token'
        )

    async def store_refresh_token(self, db: AsyncSession, user_uuid: uuid.UUID, token: str):
        user = await db.get(User, user_uuid)
        if user:
            user.google_refresh_token = token
            await db.commit()
            log.info("Stored Google refresh token for user", user_id=user_uuid)

    async def get_access_token(self, user_uuid: uuid.UUID) -> str:
        stmt = select(User.google_refresh_token).where(User.uuid == user_uuid)
        result = await self.db.execute(stmt)
        refresh_token = result.scalar_one_or_none()

        if not refresh_token:
            log.error("User has not granted Google API permissions or token is missing.", user_id=user_uuid)
            raise HTTPException(status.HTTP_403_FORBIDDEN, "User has not connected their Google account.")

        try:
            token_data = await self.oauth_client.refresh_token(
                refresh_token=refresh_token
            )
            return token_data['access_token']
        except Exception as e:
            log.error("Failed to refresh Google access token", error=str(e), user_id=user_uuid)
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not communicate with Google.")

    async def store_google_tokens(
        self,
        db: AsyncSession,
        user_uuid: uuid.UUID,
        access_token: str,
        refresh_token: str | None,
        expires_at: int,
    ):
        """Stores or updates all Google OAuth tokens for a user."""
        expires_dt = datetime.fromtimestamp(expires_at, tz=timezone.utc)
        stmt = update(User).where(User.uuid == user_uuid).values(
            google_access_token=access_token,
            google_token_expires_at=expires_dt
        )
        if refresh_token:
            stmt = stmt.values(google_refresh_token=refresh_token)
        await db.execute(stmt)
        await db.commit()
