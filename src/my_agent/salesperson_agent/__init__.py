import logging
from src.utils.logger import setup_logger

salesperson_agent_logger = setup_logger(
    "salesperson_agent",
    logging.DEBUG,
    log_file="salesperson_agent.log"
)

from . import agent
