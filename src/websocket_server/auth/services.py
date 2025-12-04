"""
Authentication services - business logic for auth operations.
"""
from typing import Optional

from src.my_agent.salesperson_agent.websocket_server.auth.schemas import UserInfo
from src.utils.jwt_utils import decode_token
from src.utils.logger import get_current_logger

logger = get_current_logger()


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
    Authenticate user via Salesperson Agent App (over WebSocket).
    Returns dict with access_token and user info, or None if failed.
    """
    from src.config import SALESPERSON_AGENT_APP_WS_URL
    from src.websocket_server.streaming.agent_stream_client import AgentStreamClient

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
