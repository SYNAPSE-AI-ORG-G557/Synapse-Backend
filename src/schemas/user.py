import uuid
from datetime import date
from pydantic import BaseModel, EmailStr, Field

# Schema for creating a new user via email/password
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(min_length=8)
    full_name: str | None = None
    date_of_birth: date | None = None

# Schema for completing a profile after Google sign-up
class ProfileCompletion(BaseModel):
    username: str
    full_name: str | None = None
    date_of_birth: date | None = None

# Public-facing user schema (omits sensitive data)
class UserPublic(BaseModel):
    uuid: uuid.UUID
    email: EmailStr
    username: str
    full_name: str | None = None
    
    class Config:
        from_attributes = True # For SQLAlchemy ORM compatibility