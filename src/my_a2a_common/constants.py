"""Shared constants used by the payment A2A examples."""

# All payloads we exchange are JSON documents.
JSON_MEDIA_TYPE = "application/json"

# Friendly names for the two agents participating in the demo flow.
SALESPERSON_AGENT_NAME = "salesperson_agent"
PAYMENT_AGENT_NAME = "payment_agent"

# Artifact names
PAYMENT_REQUEST_ARTIFACT_NAME = "payment-request"
PAYMENT_STATUS_ARTIFACT_NAME = "payment-status-request"
PAYMENT_RESPONSE_ARTIFACT_NAME = "payment-response"

__all__ = [
    "JSON_MEDIA_TYPE",
    "SALESPERSON_AGENT_NAME",
    "PAYMENT_AGENT_NAME",
    "PAYMENT_REQUEST_ARTIFACT_NAME",
    "PAYMENT_STATUS_ARTIFACT_NAME",
    "PAYMENT_RESPONSE_ARTIFACT_NAME",
]
