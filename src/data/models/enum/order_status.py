import enum


class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"