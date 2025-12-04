from typing import Optional

from starlette.websockets import WebSocket

from my_agent.salesperson_agent.websocket_server.auth import UserInfo, get_logger
from src.utils.jwt_utils import decode_token
from src.utils.logger import get_current_logger

logger = get_current_logger()


def extract_token_from_query(token: Optional[str]) -> Optional[str]:
    """Extract and validate token from query parameter."""
    if not token or not isinstance(token, str):
        return None
    return token.strip() if token.strip() else None


def extract_user_from_token(token: str) -> Optional[UserInfo]:
    """Extract user info from JWT token."""
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
    Authenticate user via MCP tool.
    Returns dict with access_token and user info, or None if failed.
    """
    from src.my_agent.salesperson_agent.salesperson_mcp_client import get_salesperson_mcp_client

    try:
        client = get_salesperson_mcp_client()
        result = await client.authenticate_user(username=username, password=password)

        if result.get("status") != "00":  # Status.SUCCESS
            logger.warning(f"Login failed via MCP: {result.get('message')}")
            return None

        logger.info(f"Login successful via MCP: username={username}")
        return result.get("data")

    except Exception as e:
        logger.exception(f"MCP authenticate_user error: {e}")
        return None


async def authenticate_websocket(
    websocket: WebSocket,
    token: Optional[str],
    session_id: str
) -> Optional[UserInfo]:
    """
    Authenticate a WebSocket connection using JWT token.
    Returns UserInfo if successful, None otherwise (connection will be closed).
    """
    logger = get_logger()

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
