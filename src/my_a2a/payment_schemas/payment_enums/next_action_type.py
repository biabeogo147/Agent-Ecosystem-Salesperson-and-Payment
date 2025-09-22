from enum import Enum


class NextActionType(str, Enum):
    NONE      = "NONE"
    ASK_USER  = "ASK_USER"
    REDIRECT  = "REDIRECT"
    SHOW_QR   = "SHOW_QR"