from typing import Annotated

from fastapi import APIRouter, Depends

from src.schemas.user import UserPublic
from src.core.dependencies import get_current_active_user

router = APIRouter()

@router.get("/me", response_model=UserPublic)
async def read_users_me(current_user: Annotated[UserPublic, Depends(get_current_active_user)]):
    """
    Get the profile of the currently authenticated user.
    
    This endpoint is protected. A valid access token must be provided
    in the 'Authorization: Bearer <token>' header.
    """
    return current_user