import logging
from src.utils.logger import setup_logger


api_gateway_logger = None

def get_api_gateway_logger():
    """Initialize API Gateway logger."""
    global api_gateway_logger
    if not api_gateway_logger:
        api_gateway_logger = setup_logger(
            name="api_gateway",
            log_level=logging.DEBUG,
            log_file="api_gateway.log",
        )
    return api_gateway_logger
