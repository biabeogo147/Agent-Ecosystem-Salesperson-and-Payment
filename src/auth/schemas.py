"""
Pydantic schemas for authentication.
"""
from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request schema."""
    username: str = Field(..., min_length=1, description="Username or email")
    password: str = Field(..., min_length=1, description="User password")


class LoginResponse(BaseModel):
    """Login response schema with JWT token."""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    expires_in: int = Field(description="Token expiration time in seconds")


class TokenPayload(BaseModel):
    """JWT token payload schema."""
    user_id: int
    username: str
    exp: Optional[int] = None


class UserInfo(BaseModel):
    """User info extracted from token."""
    user_id: int
    username: str
