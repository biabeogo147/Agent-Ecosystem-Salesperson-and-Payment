import enum


class Status(enum.Enum):
    SUCCESS = "00"
    FAILURE = "01"
    PRODUCT_NOT_FOUND = "02"
    QUANTITY_EXCEEDED = "03"
    UNKNOWN_ERROR = "99"