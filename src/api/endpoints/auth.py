import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from authlib.integrations.starlette_client import OAuth

from src.schemas.user import UserCreate, UserPublic, ProfileCompletion
from src.schemas.auth import Token
from src.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_completion_token, # New import
    verify_completion_token  # New import
)
from src.core.config import settings

# In-memory "database" for demonstration, following the Mock-First paradigm.
FAKE_USERS_DB = {}
# ++ ADDED START ++
# Add a new in-memory store for Google users for the mock implementation
FAKE_GOOGLE_USERS_DB = {}
# ++ ADDED END ++

router = APIRouter()

# ++ ADDED START ++
# --- Configure Authlib OAuth Client ---
oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# --- New Dependency for Profile Completion ---
completion_token_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/complete-profile")

def get_completion_token_payload(token: Annotated[str, Depends(completion_token_scheme)]) -> dict:
    return verify_completion_token(token)
# ++ ADDED END ++


# Dependency to get the refresh token from the secure cookie
def get_refresh_token_from_cookie(request: Request) -> str | None:
    return request.cookies.get("refresh_token")

@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate):
    """
    Handles user registration. Hashes the password and stores the new user.
    """
    if user_in.email in FAKE_USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    hashed_password = get_password_hash(user_in.password)
    user_db_data = user_in.model_dump()
    user_db_data.pop("password")
    user_db_data["hashed_password"] = hashed_password
    
    user_db_data["uuid"] = uuid.uuid4()
    
    FAKE_USERS_DB[user_in.email] = user_db_data
    
    return user_db_data

@router.post("/token", response_model=Token)
async def login_for_access_token(response: Response, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """
    Authenticates user and returns access and refresh tokens.
    This follows the OAuth2 "Password Flow".
    """
    user = FAKE_USERS_DB.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user["email"]})
    refresh_token = create_refresh_token(data={"sub": user["email"]})
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="strict",
        secure=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

# ++ ADDED START ++
# --- New Google OAuth2 Endpoints ---

@router.get("/google/login")
async def google_login(request: Request):
    """
    Redirects the user to Google's OAuth2 consent screen.
    """
    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, str(redirect_uri))

@router.get("/google/callback")
async def google_callback(request: Request, response: Response):
    """
    Handles the callback from Google after user authentication.
    """
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')
    
    if not user_info:
        raise HTTPException(status_code=400, detail="Could not retrieve user info from Google")

    google_provider_id = user_info['sub']
    user_email = user_info['email']

    # Returning user
    if google_provider_id in FAKE_GOOGLE_USERS_DB:
        user = FAKE_USERS_DB.get(user_email)
        access_token = create_access_token(data={"sub": user["email"]})
        refresh_token = create_refresh_token(data={"sub": user["email"]})
        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)

        # Redirect to frontend with success message
        redirect_url = f"http://localhost:3000/auth-success?message=Google%20authentication%20complete"
        return RedirectResponse(url=redirect_url)

    # New registration
    completion_token = create_completion_token(
        data={
            "google_provider_id": google_provider_id,
            "email": user_email,
            "full_name": user_info.get('name')
        }
    )
    # Redirect to frontend for completing profile
    redirect_url = f"http://localhost:3000/complete-profile?token={completion_token}"
    return RedirectResponse(url=redirect_url)
@router.patch("/complete-profile", response_model=Token)
async def complete_google_user_profile(
    response: Response,
    profile_data: ProfileCompletion,
    payload: Annotated[dict, Depends(get_completion_token_payload)]
):
    """
    Finalizes registration for a new user who signed up with Google.
    Requires a valid 'completion_token'.
    """
    google_provider_id = payload.get("google_provider_id")
    email = payload.get("email")
    full_name = payload.get("full_name")

    # Check if username is already taken
    for user in FAKE_USERS_DB.values():
        if user.get("username") == profile_data.username:
            raise HTTPException(status_code=400, detail="Username is already taken")

    # Create the new user in our mock DBs
    new_user_data = {
        "uuid": uuid.uuid4(),
        "email": email,
        "username": profile_data.username,
        "full_name": full_name,
        "date_of_birth": profile_data.date_of_birth,
        "hashed_password": None, # No password for Google users
        "google_provider_id": google_provider_id,
        "is_active": True
    }
    FAKE_USERS_DB[email] = new_user_data
    FAKE_GOOGLE_USERS_DB[google_provider_id] = email

    # Issue final access and refresh tokens
    access_token = create_access_token(data={"sub": email})
    refresh_token = create_refresh_token(data={"sub": email})
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
    
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
# ++ ADDED END ++

@router.post("/refresh", response_model=Token)
async def refresh_access_token(response: Response, refresh_token: Annotated[str | None, Depends(get_refresh_token_from_cookie)]):
    """
    Refreshes an expired access token using a valid refresh token from an HttpOnly cookie.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found in cookie",
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            refresh_token, settings.JWT_REFRESH_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = FAKE_USERS_DB.get(email)
    if user is None:
        raise credentials_exception
        
    new_access_token = create_access_token(data={"sub": email})
    new_refresh_token = create_refresh_token(data={"sub": email})

    response.set_cookie(key="refresh_token", value=new_refresh_token, httponly=True, samesite="strict", secure=True)

    return {"access_token": new_access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}