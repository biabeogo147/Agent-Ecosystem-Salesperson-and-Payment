"""
Custom Chat UI for Salesperson Agent.

A simple chat interface that replaces ADK web, with integrated WebSocket
support for real-time payment notifications.
"""
import logging


def get_chat_ui_logger():
    from src.utils.logger import setup_logger
    return setup_logger(
        "chat_ui",
        logging.DEBUG,
        log_file="chat_ui.log"
    )


chat_ui_logger = get_chat_ui_logger()
