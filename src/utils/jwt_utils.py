"""
JWT utility functions for authentication.

Provides functions to create, decode, and verify JWT tokens.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from pydantic import BaseModel

from src.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES


class TokenPayload(BaseModel):
    """JWT token payload schema."""
    user_id: int
    username: str
    exp: Optional[datetime] = None


def create_access_token(
    user_id: int,
    username: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: The user's ID
        username: The user's username
        expires_delta: Optional expiration time delta. Defaults to JWT_EXPIRE_MINUTES.

    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)

    payload = {
        "user_id": user_id,
        "username": username,
        "exp": expire
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode a JWT token and return its payload.

    Args:
        token: The JWT token string

    Returns:
        Decoded payload dictionary

    Raises:
        jwt.ExpiredSignatureError: If the token has expired
        jwt.InvalidTokenError: If the token is invalid
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def verify_token(token: str) -> Optional[int]:
    """
    Verify a JWT token and return the user_id if valid.

    Args:
        token: The JWT token string

    Returns:
        user_id if token is valid, None otherwise
    """
    try:
        payload = decode_token(token)
        return payload.get("user_id")
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_token_payload(token: str) -> Optional[TokenPayload]:
    """
    Get the full token payload as a Pydantic model.

    Args:
        token: The JWT token string

    Returns:
        TokenPayload if valid, None otherwise
    """
    try:
        payload = decode_token(token)
        return TokenPayload(
            user_id=payload.get("user_id"),
            username=payload.get("username"),
            exp=datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc) if payload.get("exp") else None
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
