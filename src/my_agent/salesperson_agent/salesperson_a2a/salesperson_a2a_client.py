"""Convenience wrapper for the salesperson agent to call the payment agent."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from config import PAYMENT_AGENT_SERVER_HOST, PAYMENT_AGENT_SERVER_PORT
from my_a2a_common import extract_payment_response

from my_agent.base_a2a_client import BaseA2AClient
from my_agent.salesperson_agent.salesperson_a2a.payment_tasks import (
    prepare_create_order_payload,
    prepare_query_status_payload,
)
from utils.response_format_a2a import ResponseFormatA2A


PAYMENT_AGENT_BASE_URL = f"http://{PAYMENT_AGENT_SERVER_HOST}:{PAYMENT_AGENT_SERVER_PORT}"


class SalespersonA2AClient(BaseA2AClient):
    """Client used by the salesperson agent to reach the payment service."""

    def __init__(self, *, base_url: str | None = None, **kwargs: Any) -> None:
        super().__init__(
            base_url=base_url or PAYMENT_AGENT_BASE_URL,
            endpoint_path="/",
            **kwargs,
        )

    async def create_order(
        self,
        items: Sequence[Mapping[str, Any]] | Sequence[Any],
        customer: Mapping[str, Any] | Any,
        channel: str,
        *,
        note: str | None = None,
        metadata: Dict[str, str] | None = None,
    ) -> ResponseFormatA2A:
        """Create an order by preparing the payload and forwarding it to A2A."""

        metadata_payload = dict(metadata) if metadata is not None else None
        payload = await prepare_create_order_payload(
            list(items),
            customer,
            channel,
            note=note,
            metadata=metadata_payload,
        )
        message = await self.send_task_payload(payload)
        response = extract_payment_response(message)

        return ResponseFormatA2A(
            data={
                "message": message.model_dump(mode="json"),
                "response": response.model_dump(mode="json"),
            }
        )

    async def query_status(self, correlation_id: str) -> ResponseFormatA2A:
        """Query the payment agent for the status of a previously created order."""

        payload = await prepare_query_status_payload(correlation_id)
        message = await self.send_task_payload(payload)
        response = extract_payment_response(message)

        return ResponseFormatA2A(
            data={
                "message": message.model_dump(mode="json"),
                "response": response.model_dump(mode="json"),
            }
        )


__all__ = ["SalespersonA2AClient", "PAYMENT_AGENT_BASE_URL"]
