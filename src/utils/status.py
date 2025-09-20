import enum


class Status(enum.Enum):
    SUCCESS = "00"
    FAILURE = "01"
    UNKNOWN_ERROR = "99"