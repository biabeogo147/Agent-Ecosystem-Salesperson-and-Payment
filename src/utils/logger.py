import logging
import sys
import os
from logging.handlers import RotatingFileHandler

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
