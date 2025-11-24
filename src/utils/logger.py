"""
Logger utilities for multi-app architecture with context-aware logging.

This module provides:
1. setup_logger() - Function to create configured logger instances
2. Context-aware logging that allows shared infrastructure (data layer) to
   automatically use the logger of the calling app

Usage:
    # Setting up a basic logger:
    from src.utils.logger import setup_logger
    my_logger = setup_logger("my_app", logging.INFO, "my_app.log")

    # In app entry point (context-aware):
    from src.utils.logger import set_app_context, AppLogger
    with set_app_context(AppLogger.PAYMENT_MCP):
        # All data layer calls will use payment_mcp_logger
        product = find_product_by_sku("SKU001")

    # In shared infrastructure:
    from src.utils.logger import get_current_logger
    logger = get_current_logger()
    logger.info("This logs to the calling app's logger")
"""

import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from contextvars import ContextVar
from enum import Enum
from typing import Optional

# Create logs directory if it doesn't exist
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, "app.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "error.log")


def setup_logger(name: str = "app_logger", log_level: int = logging.INFO, log_file: str = None):
    """
    Sets up a logger with both console and file handlers.

    Args:
        name (str): The name of the logger.
        log_level (int): The logging level (default: logging.INFO).
        log_file (str): Optional custom log filename (without path). If not provided, defaults to "{name}.log".

    Returns:
        logging.Logger: The configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Check if handlers are already added to avoid duplicate logs
    if not logger.handlers:
        # Determine log file names
        if log_file is None:
            log_file = f"{name}.log"

        app_log_file = os.path.join(LOG_DIR, log_file)
        error_log_file = os.path.join(LOG_DIR, f"{os.path.splitext(log_file)[0]}_error.log")

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File Handler (Rotating) - App Log
        file_handler = RotatingFileHandler(
            app_log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # File Handler (Rotating) - Error Log
        error_file_handler = RotatingFileHandler(
            error_log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
        )
        error_file_handler.setFormatter(formatter)
        error_file_handler.setLevel(logging.ERROR)
        logger.addHandler(error_file_handler)

    return logger


# Default logger instance
logger = setup_logger()


# ============================================================================
# Context-Aware Logging for Multi-App Architecture
# ============================================================================

class AppLogger(Enum):
    """Enum of available app loggers."""
    A2A_PAYMENT = "a2a_payment"
    PAYMENT_MCP = "payment_mcp"
    SALESPERSON_AGENT = "salesperson_agent"
    SALESPERSON_MCP = "salesperson_mcp"
    WEBHOOK = "webhook"
    DEFAULT = "app_logger"


# Context variable to track current app logger
_current_app_logger: ContextVar[AppLogger] = ContextVar('current_app_logger', default=AppLogger.DEFAULT)


def get_current_logger() -> logging.Logger:
    """
    Get the logger for the current app context.

    This function is used by shared infrastructure (data layer) to automatically
    use the correct logger based on which app is calling it.

    Returns:
        logging.Logger: The logger instance for the current app context
    """
    app_logger_type = _current_app_logger.get()

    # Import loggers lazily to avoid circular imports
    if app_logger_type == AppLogger.A2A_PAYMENT:
        from src.my_agent.payment_agent import a2a_payment_logger
        return a2a_payment_logger

    elif app_logger_type == AppLogger.PAYMENT_MCP:
        from src.my_mcp.payment import payment_mcp_logger
        return payment_mcp_logger

    elif app_logger_type == AppLogger.SALESPERSON_AGENT:
        from src.my_agent.salesperson_agent import salesperson_agent_logger
        return salesperson_agent_logger

    elif app_logger_type == AppLogger.SALESPERSON_MCP:
        from src.my_mcp.salesperson import salesperson_mcp_logger
        return salesperson_mcp_logger

    elif app_logger_type == AppLogger.WEBHOOK:
        from src.web_hook import webhook_logger
        return webhook_logger

    else:
        # Fallback to default logger defined above
        return logger


class set_app_context:
    """
    Context manager to set the current app logger context.

    Usage:
        with set_app_context(AppLogger.PAYMENT_MCP):
            # All get_current_logger() calls will return payment_mcp_logger
            result = some_data_layer_function()
    """

    def __init__(self, app_logger: AppLogger):
        self.app_logger = app_logger
        self.token: Optional[object] = None

    def __enter__(self):
        self.token = _current_app_logger.set(self.app_logger)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token is not None:
            _current_app_logger.reset(self.token)
        return False


def get_current_app_name() -> str:
    """
    Get the name of the current app context.

    Returns:
        str: Name of the current app (e.g., "payment_mcp", "salesperson_mcp")
    """
    app_logger_type = _current_app_logger.get()
    return app_logger_type.value
