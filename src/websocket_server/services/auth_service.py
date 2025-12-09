from typing import Optional

from fastapi import WebSocket, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.utils.jwt_utils import decode_token
from src.utils.logger import get_current_logger
from src.websocket_server.schemas import UserInfo


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
    Authenticate user via Salesperson Agent App (over WebSocket).
    Returns dict with access_token and user info, or None if failed.
    """
    from src.config import SALESPERSON_AGENT_APP_WS_URL
    from src.websocket_server.utils.agent_stream_client import AgentStreamClient

    logger = get_current_logger()

    try:
        async with AgentStreamClient(SALESPERSON_AGENT_APP_WS_URL) as agent_client:
            # Send authentication request
            await agent_client.send({
                "type": "authenticate",
                "username": username,
                "password": password
            })

            # Wait for response
            async for msg in agent_client.receive():
                msg_type = msg.get("type")

                if msg_type == "authenticate_response":
                    if msg.get("status") == "success":
                        logger.info(f"Login successful via Agent App: username={username}")
                        return msg.get("data")
                    else:
                        logger.warning(f"Login failed via Agent App: {msg.get('message')}")
                        return None

                elif msg_type == "error":
                    logger.error(f"Agent App returned error during auth: {msg.get('message')}")
                    return None

            return None

    except Exception as e:
        logger.exception(f"authenticate_user error: {e}")
        return None


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
    from src.websocket_server import get_ws_server_logger

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
