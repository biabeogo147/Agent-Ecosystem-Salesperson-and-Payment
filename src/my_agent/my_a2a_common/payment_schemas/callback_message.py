from pydantic import BaseModel


class CallbackMessage(BaseModel):
    order_id: int
    timestamp: str
