import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError # ✨ NEW: Import ValidationError for robust error handling

from src.core.config import settings
from src.schemas.auth import TokenPayload
from src.db.database import get_db_session
from src.services.user_service import UserService
from src.db import models # ✨ FIX 1: Import the 'models' module

# This scheme points to the /token endpoint for the API docs.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user_service: UserService = Depends()
) -> models.User:
    """
    Decodes the access token, validates the UUID, and returns the user from the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        # The 'sub' claim now contains the user's UUID
        user_uuid_str: str = payload.get("sub")
        if user_uuid_str is None:
            raise credentials_exception
        token_data = TokenPayload(sub=user_uuid_str)
    except JWTError:
        raise credentials_exception
    
    # Retrieve user from the database using the UUID
    user = await user_service.get_user_by_uuid(id=uuid.UUID(token_data.sub), db=db)
    if user is None:
        raise credentials_exception
        
    return user

async def get_current_active_user(
    current_user: Annotated[models.User, Depends(get_current_user)]
) -> models.User:
    """
    A composable dependency that gets the current user and checks if they are active.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# ✨ --- THIS IS THE CORRECTED NEW FUNCTION --- ✨
async def get_user_from_token(
    token: str, 
    db: AsyncSession,
    user_service: UserService = Depends() # ✨ FIX 2: Use UserService like get_current_user
) -> models.User | None:
    """
    Decodes a JWT token provided as a string and fetches the user.
    Used for authenticating via URL query parameters (e.g., for file exports).
    Returns the user object or None if validation fails.
    """
    if not token:
        return None
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_uuid_str = payload.get("sub")
        if not user_uuid_str:
            return None
        
        token_data = TokenPayload(sub=user_uuid_str)
        
        # ✨ FIX 3: Use the user_service to get the user by UUID
        user = await user_service.get_user_by_uuid(id=uuid.UUID(token_data.sub), db=db)

        if not user or not user.is_active:
            return None
        return user
    except (JWTError, ValidationError): # ✨ FIX 4: Catch JWTError and ValidationError
        return None
# ✨ ----------------------------------------------- ✨