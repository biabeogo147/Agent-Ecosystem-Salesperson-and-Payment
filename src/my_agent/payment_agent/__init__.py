import logging
from src.utils.logger import setup_logger

a2a_payment_logger = setup_logger(
    "a2a_payment",
    logging.DEBUG,
    log_file="a2a_payment.log"
)

from . import agent