"""Convenience wrapper for the salesperson agent to call the payment agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from a2a.types import Message, Task

from config import PAYMENT_AGENT_SERVER_HOST, PAYMENT_AGENT_SERVER_PORT
from my_a2a_common import extract_payment_response
from my_a2a_common.payment_schemas import PaymentResponse

from my_agent.base_a2a_client import BaseA2AClient


PAYMENT_AGENT_BASE_URL = f"http://{PAYMENT_AGENT_SERVER_HOST}:{PAYMENT_AGENT_SERVER_PORT}"


@dataclass
class PaymentAgentResult:
    """Structured representation of the payment agent's reply."""

    message: Message
    response: PaymentResponse

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of the result for logging or tests."""

        return {
            "message": self.message.model_dump(mode="json"),
            "response": self.response.model_dump(mode="json"),
        }


class SalespersonA2AClient(BaseA2AClient):
    """Client used by the salesperson agent to reach the payment service."""

    def __init__(self, *, base_url: str | None = None, **kwargs: Any) -> None:
        super().__init__(
            base_url=base_url or PAYMENT_AGENT_BASE_URL,
            endpoint_path="/",
            **kwargs,
        )

    @staticmethod
    def _task_from_payload(payload: Mapping[str, Any]) -> Task:
        task_payload = payload.get("task")
        if task_payload is None:
            raise ValueError("Expected payload to contain 'task' entry")
        return Task.model_validate(task_payload)

    async def create_order(self, payload: Mapping[str, Any]) -> PaymentAgentResult:
        """Send the create-order task to the payment agent and parse the reply."""

        task = self._task_from_payload(payload)
        message = await self.send_task(task)
        response = extract_payment_response(message)
        return PaymentAgentResult(message=message, response=response)

    async def query_status(self, payload: Mapping[str, Any]) -> PaymentAgentResult:
        """Send the status lookup task to the payment agent and parse the reply."""

        task = self._task_from_payload(payload)
        message = await self.send_task(task)
        response = extract_payment_response(message)
        return PaymentAgentResult(message=message, response=response)


__all__ = ["PaymentAgentResult", "SalespersonA2AClient", "PAYMENT_AGENT_BASE_URL"]
