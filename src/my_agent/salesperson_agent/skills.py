import uuid

from config import *

from google.adk.tools import FunctionTool



def correlation_id(prefix: str) -> str:
    """Generate a unique correlation ID with the given prefix for A2A interactions."""
    return f"{prefix}-{str(uuid.uuid4())}"


def get_return_cancel_url_for_payment(correlation_id: str) -> tuple[str, str]:
    """Generate return and cancel URLs for payment with the given correlation ID."""
    return (f"{RETURN_URL}?cid={correlation_id}",
            f"{CANCEL_URL}?cid={correlation_id}")


correlation_id_tool = FunctionTool(correlation_id)
get_return_cancel_url_for_payment_tool = FunctionTool(get_return_cancel_url_for_payment)