from typing import Optional

from fastapi import WebSocket, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.utils.jwt_utils import decode_token
from src.utils.logger import get_current_logger
from src.api_gateway.schemas import UserInfo


# HTTP Bearer token scheme for REST endpoints
bearer_scheme = HTTPBearer()


def extract_user_from_token(token: str) -> Optional[UserInfo]:
    """Extract user info from JWT token."""
    logger = get_current_logger()
    try:
        payload = decode_token(token)
        user_id = payload.get("user_id")
        username = payload.get("username")
        if user_id is None:
            return None
        return UserInfo(user_id=int(user_id), username=username)
    except Exception as e:
        logger.warning(f"Failed to decode JWT token: {e}")
        return None


async def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Authenticate user directly via database.
    Returns dict with access_token and user info, or None if failed.
    """
    from sqlalchemy import select, or_
    from passlib.context import CryptContext
    from src.data.models.db_entity.user import User
    from src.data.postgres.connection import db_connection
    from src.utils.jwt_utils import create_access_token
    from src.config import JWT_EXPIRE_MINUTES

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    logger = get_current_logger()

    session = db_connection.get_session()
    try:
        result = await session.execute(
            select(User).where(or_(User.username == username, User.email == username))
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"Login failed: user not found - {username}")
            return None

        if not pwd_context.verify(password, user.hashed_password):
            logger.warning(f"Login failed: invalid password - {username}")
            return None

        access_token = create_access_token(user_id=user.id, username=user.username)
        logger.info(f"Login successful: user_id={user.id}, username={user.username}")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username,
            "expires_in": JWT_EXPIRE_MINUTES * 60
        }
    except Exception as e:
        logger.exception(f"authenticate_user error: {e}")
        return None
    finally:
        await session.close()


def extract_token_from_query(token: Optional[str]) -> Optional[str]:
    """Extract and validate token from query parameter."""
    if not token or not isinstance(token, str):
        return None
    return token.strip() if token.strip() else None


async def authenticate_websocket(
    websocket: WebSocket,
    token: Optional[str],
    session_id: str
) -> Optional[UserInfo]:
    """
    Authenticate a WebSocket connection using JWT token.
    Returns UserInfo if successful, None otherwise (connection will be closed).
    """
    from src.api_gateway import get_api_gateway_logger

    logger = get_api_gateway_logger()

    if not token:
        logger.warning(f"WebSocket rejected: missing token for session {session_id}")
        await websocket.close(code=4001, reason="Missing authentication token")
        return None

    user_info = extract_user_from_token(token)
    if not user_info:
        logger.warning(f"WebSocket rejected: invalid token for session {session_id}")
        await websocket.close(code=4002, reason="Invalid or expired token")
        return None

    logger.info(f"WebSocket authenticated: session_id={session_id}, user_id={user_info.user_id}")
    return user_info


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> UserInfo:
    """
    FastAPI dependency to extract and validate user from Bearer token.
    Use with REST endpoints that require authentication.

    Usage:
        @router.get("/protected")
        async def protected_endpoint(current_user: UserInfo = Depends(get_current_user)):
            return {"user_id": current_user.user_id}

    Raises:
        HTTPException 401: If token is missing, invalid, or expired
    """
    user_info = extract_user_from_token(credentials.credentials)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user_info
