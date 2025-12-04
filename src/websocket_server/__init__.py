"""WebSocket Server package for real-time notifications."""

import logging

from src.utils.logger import setup_logger

# Initialize logger for WebSocket Server
ws_server_logger = setup_logger(
    name="websocket_server",
    log_file="logs/websocket_server.log"
)
