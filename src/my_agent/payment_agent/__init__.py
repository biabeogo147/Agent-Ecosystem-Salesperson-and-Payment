from . import agent

import logging

def get_a2a_payment_logger():
    from src.utils.logger import setup_logger
    return setup_logger(
        "a2a_payment",
        logging.DEBUG,
        log_file="a2a_payment.log"
    )

a2a_payment_logger = get_a2a_payment_logger()