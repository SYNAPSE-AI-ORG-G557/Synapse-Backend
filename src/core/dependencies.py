from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from src.core.config import settings
from src.schemas.auth import TokenPayload
from src.schemas.user import UserPublic
# This is a placeholder for our mock database from the auth endpoint
# In a real application, this would import a database service.
from src.api.endpoints.auth import FAKE_USERS_DB 

# This scheme will extract the token from the Authorization header
# and check that it contains "Bearer". The tokenUrl points to the
# endpoint that issues the token, which is used for the API docs.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserPublic:
    """
    Decodes the access token, validates it, and returns the current user.
    Raises an HTTPException if the token is invalid or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the JWT using the access token secret key
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM] # FIX: Correctly pass algorithms as a list
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenPayload(sub=email)
    except JWTError:
        # This catches any error from jose, like invalid signature or expired token
        raise credentials_exception
    
    # Retrieve user from our mock database
    user_data = FAKE_USERS_DB.get(token_data.sub)
    if user_data is None:
        raise credentials_exception
        
    return UserPublic(**user_data)

def get_current_active_user(current_user: Annotated[UserPublic, Depends(get_current_user)]) -> UserPublic:
    """
    A composable dependency that first gets the current user, then checks
    if they are active. In a real app, you'd check a database field.
    """
    # In a real application with a database, you would check a field like `is_active`.
    # For our mock implementation, we'll assume all users are active.
    # if not current_user.is_active:
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user