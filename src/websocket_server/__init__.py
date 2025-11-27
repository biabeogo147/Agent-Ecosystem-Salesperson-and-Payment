"""
WebSocket server for real-time payment notifications.

This service provides real-time push notifications to frontend clients
when payment status updates are received via Redis Pub/Sub.
"""
import logging


def get_ws_server_logger():
    from src.utils.logger import setup_logger
    return setup_logger(
        "websocket_server",
        logging.DEBUG,
        log_file="websocket_server.log"
    )


ws_server_logger = get_ws_server_logger()
