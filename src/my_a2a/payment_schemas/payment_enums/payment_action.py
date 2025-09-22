from enum import Enum


class PaymentAction(str, Enum):
    CREATE_ORDER  = "CREATE_ORDER"
    QUERY_STATUS  = "QUERY_STATUS"
    CANCEL        = "CANCEL"