import logging
from src.utils.logger import setup_logger

payment_mcp_logger = setup_logger("payment_mcp", logging.DEBUG, log_file="server_payment_tool.log")