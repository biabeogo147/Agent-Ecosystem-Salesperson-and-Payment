from enum import Enum


class PaymentChannel(str, Enum):
    REDIRECT = "redirect"
    QR       = "qr"