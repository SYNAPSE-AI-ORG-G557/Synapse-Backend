from fastapi import APIRouter, Depends
from src.services.google_auth_service import GoogleAuthService
from src.core.dependencies import get_current_active_user
from src.db.models import User as UserModel

router = APIRouter(prefix="/internal/auth", tags=["Internal Auth"])

@router.get("/google_token")
async def get_google_access_token(
    current_user: UserModel = Depends(get_current_active_user),
    google_service: GoogleAuthService = Depends()
):
    access_token = await google_service.get_access_token(current_user.uuid)
    return {"access_token": access_token}
