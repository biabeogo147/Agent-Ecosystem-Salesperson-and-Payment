"""Shared constants used by the payment A2A examples."""

# All payloads we exchange are JSON documents.
JSON_MEDIA_TYPE = "application/json"

# Labels used in DataPart metadata to describe the structure contained within.
PAYMENT_REQUEST_KIND = "payment-request"
PAYMENT_STATUS_KIND = "payment-status-request"
PAYMENT_RESPONSE_KIND = "payment-response"

# Friendly names for the two agents participating in the demo flow.
SALESPERSON_AGENT_NAME = "salesperson_agent"
PAYMENT_AGENT_NAME = "payment_agent"

__all__ = [
    "JSON_MEDIA_TYPE",
    "PAYMENT_REQUEST_KIND",
    "PAYMENT_STATUS_KIND",
    "PAYMENT_RESPONSE_KIND",
    "SALESPERSON_AGENT_NAME",
    "PAYMENT_AGENT_NAME",
]
