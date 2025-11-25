from src.utils.logger import setup_logger

callback_logger = setup_logger("payment_callback", log_file="payment_callback.log")

__all__ = ["callback_logger"]
