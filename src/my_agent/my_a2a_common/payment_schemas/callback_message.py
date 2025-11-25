from pydantic import BaseModel


class CallbackMessage(BaseModel):
    """
    Simplified message format for payment callback published via Redis Pub/Sub.

    This message is published by Callback Service and consumed by Payment Agent.
    Only contains order_id - Payment Agent will query gateway for actual status.
    """
    order_id: str
    timestamp: str  # ISO 8601 format
