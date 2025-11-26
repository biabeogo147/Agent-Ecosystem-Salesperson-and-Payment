from pydantic import BaseModel


class CallbackMessage(BaseModel):
    order_id: str
    timestamp: str
