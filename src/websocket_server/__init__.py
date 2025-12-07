import logging
from src.utils.logger import setup_logger


ws_server_logger = None

def get_ws_server_logger():
    """Initialize WebSocket server logger."""
    global ws_server_logger
    if not ws_server_logger:
        ws_server_logger = setup_logger(
            name="websocket_server",
            log_level=logging.DEBUG,
            log_file="websocket_server.log",
        )
    return ws_server_logger
