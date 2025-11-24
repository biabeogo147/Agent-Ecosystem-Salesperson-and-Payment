import logging
from src.utils.logger import setup_logger

webhook_logger = setup_logger(
    "webhook",
    logging.DEBUG,
    log_file="webhook_app.log"
)
