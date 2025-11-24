from . import agent

import logging

def get_salesperson_agent_logger():
    from src.utils.logger import setup_logger
    return setup_logger(
        "salesperson_agent",
        logging.DEBUG,
        log_file="salesperson_agent.log"
    )

salesperson_agent_logger = get_salesperson_agent_logger()