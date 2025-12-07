"""
Authentication module for WebSocket server.
"""
from typing import Optional

from fastapi import WebSocket

from src.websocket_server.auth.router import router as auth_router
from src.websocket_server.auth.schemas import UserInfo
from src.websocket_server.auth.services import extract_user_from_token
from src.websocket_server import get_ws_server_logger


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
    logger = get_ws_server_logger()

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


__all__ = [
    "auth_router",
    "UserInfo",
    "authenticate_websocket",
    "extract_token_from_query",
    "extract_user_from_token",
]
