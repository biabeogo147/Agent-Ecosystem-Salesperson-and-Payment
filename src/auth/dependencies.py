"""
FastAPI dependencies for authentication.
"""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.auth.schemas import UserInfo
from src.utils.jwt_utils import decode_token

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserInfo:
    """
    Get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Authorization credentials (Bearer token)

    Returns:
        UserInfo with user_id and username

    Raises:
        HTTPException: If token is missing, expired, or invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("user_id")
        username = payload.get("username")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return UserInfo(user_id=user_id, username=username)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[UserInfo]:
    """
    Get the current user if authenticated, or None if not.

    This is useful for endpoints that work with or without authentication.

    Args:
        credentials: HTTP Authorization credentials (Bearer token)

    Returns:
        UserInfo if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("user_id")
        username = payload.get("username")

        if user_id is None:
            return None

        return UserInfo(user_id=user_id, username=username)
    except Exception:
        return None


def extract_token_from_header(authorization: str) -> Optional[str]:
    """
    Extract JWT token from Authorization header.

    Args:
        authorization: Authorization header value (e.g., "Bearer <token>")

    Returns:
        Token string if valid Bearer format, None otherwise
    """
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]
