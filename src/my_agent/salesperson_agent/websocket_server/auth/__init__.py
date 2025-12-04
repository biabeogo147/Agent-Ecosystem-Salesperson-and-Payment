from my_agent.salesperson_agent.websocket_server.auth.services import extract_token_from_query, authenticate_websocket
from src.my_agent.salesperson_agent.websocket_server.auth.router import router as auth_router
from src.my_agent.salesperson_agent.websocket_server.auth.schemas import UserInfo
from src.my_agent.salesperson_agent.websocket_server.auth.services import extract_user_from_token

_logger = None


def get_logger():
    global _logger
    if _logger is None:
        from src.my_agent.salesperson_agent.websocket_server import ws_server_logger
        _logger = ws_server_logger
    return _logger
