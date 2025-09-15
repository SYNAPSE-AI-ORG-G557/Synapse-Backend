import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from authlib.integrations.starlette_client import OAuth
from jose import JWTError, jwt

from src.schemas.user import UserCreate, UserPublic, ProfileCompletion
from src.schemas.auth import Token
from src.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    create_completion_token,
    verify_completion_token
)
from src.core.config import settings
from src.db.database import get_db_session
from src.services.user_service import UserService

router = APIRouter()
oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# --- Dependency for Profile Completion ---
completion_token_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/complete-profile")

def get_completion_token_payload(token: Annotated[str, Depends(completion_token_scheme)]) -> dict:
    return verify_completion_token(token)

# --- Dependency to get refresh token from cookie ---
def get_refresh_token_from_cookie(request: Request) -> str | None:
    return request.cookies.get("refresh_token")


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user_service: UserService = Depends()
):
    db_user_by_email = await user_service.get_user_by_email(email=user_in.email, db=db)
    if db_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered",
        )
    
    db_user_by_username = await user_service.get_user_by_username(username=user_in.username, db=db)
    if db_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken",
        )
        
    return await user_service.create_user_from_email(user_in=user_in, db=db)

@router.post("/token", response_model=Token)
async def login_for_access_token(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: UserService = Depends()
):
    user = await user_service.get_user_by_email(email=form_data.username, db=db)
    if not user or not user.hashed_password or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.uuid)})
    refresh_token = create_refresh_token(data={"sub": str(user.uuid)})
    
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.get("/google/login")
async def google_login(request: Request):
    """
    Redirects the user to Google's OAuth2 consent screen.
    """
    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, str(redirect_uri))

@router.get("/google/callback")
async def google_callback(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user_service: UserService = Depends()
):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')
    
    google_provider_id = user_info['sub']
    user = await user_service.get_user_by_google_id(google_id=google_provider_id, db=db)

    if user:  # Returning user
        access_token = create_access_token(data={"sub": str(user.uuid)})
        refresh_token = create_refresh_token(data={"sub": str(user.uuid)})
        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
        return RedirectResponse(url="/docs")

    # New user registration
    completion_token = create_completion_token(
        data={"google_provider_id": google_provider_id, "email": user_info['email'], "full_name": user_info.get('name')}
    )
    # Change it to this:
    redirect_url = f"http://localhost:4173/complete-profile?token={completion_token}"
    return RedirectResponse(url=redirect_url)

@router.patch("/complete-profile", response_model=Token)
async def complete_google_user_profile(
    response: Response,
    profile_data: ProfileCompletion,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    payload: Annotated[dict, Depends(get_completion_token_payload)],
    user_service: UserService = Depends()
):
    if await user_service.get_user_by_username(username=profile_data.username, db=db):
        raise HTTPException(status_code=400, detail="Username is already taken")
    
    user = await user_service.create_user_from_google(
        profile_data=profile_data,
        google_id=payload.get("google_provider_id"),
        email=payload.get("email"),
        full_name=payload.get("full_name"),
        db=db
    )
    
    access_token = create_access_token(data={"sub": str(user.uuid)})
    refresh_token = create_refresh_token(data={"sub": str(user.uuid)})
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user_service: UserService = Depends(),
    refresh_token: Annotated[str | None, Depends(get_refresh_token_from_cookie)] = None
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found in cookie",
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
    )
    try:
        payload = jwt.decode(
            refresh_token, settings.JWT_REFRESH_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_uuid_str: str = payload.get("sub")
        if user_uuid_str is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await user_service.get_user_by_uuid(id=uuid.UUID(user_uuid_str), db=db)
    if user is None or not user.is_active:
        raise credentials_exception
        
    new_access_token = create_access_token(data={"sub": str(user.uuid)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.uuid)})

    response.set_cookie(key="refresh_token", value=new_refresh_token, httponly=True, samesite="strict", secure=True)

    return {"access_token": new_access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}