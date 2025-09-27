"""HTTP client used by the salesperson agent to talk to the payment agent."""

from __future__ import annotations

import json
from typing import Any, Mapping
from uuid import uuid4

from a2a.types import MessageSendParams, SendMessageRequest, Task
from pydantic import ValidationError

from my_agent.base_a2a_client import BaseA2AClient
from my_agent.salesperson_agent.salesperson_a2a.remote_agent import (
    get_payment_agent_card,
)


class SalespersonA2AClient(BaseA2AClient):
    """Concrete A2A client dedicated to payment operations."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        super().__init__(base_url=base_url, token=token, timeout=timeout)

    async def create_order(self, payload: Mapping[str, Any] | str) -> Mapping[str, Any]:
        """Send the ``create_order`` task to the payment agent."""

        envelope = self._normalise_task_envelope(payload, operation="create_order")
        request = self._build_send_message_request(envelope, operation="create_order")
        response = await self._post_json("/", request)
        data = self._extract_success_data(response, operation="create_order")
        if not isinstance(data, Mapping):
            raise RuntimeError(
                "A2A operation 'create_order' returned non-mapping data payload"
            )
        return data

    async def query_status(self, payload: Mapping[str, Any] | str) -> Mapping[str, Any]:
        """Send the ``query_status`` task to the payment agent."""

        envelope = self._normalise_task_envelope(payload, operation="query_status")
        request = self._build_send_message_request(envelope, operation="query_status")
        response = await self._post_json("/", request)
        data = self._extract_success_data(response, operation="query_status")
        if not isinstance(data, Mapping):
            raise RuntimeError(
                "A2A operation 'query_status' returned non-mapping data payload"
            )
        return data

    def _normalise_task_envelope(
        self,
        envelope: Mapping[str, Any] | str,
        *,
        operation: str,
    ) -> dict[str, Any]:
        """Coerce envelopes passed by the agent into serialisable dictionaries."""

        if isinstance(envelope, str):
            try:
                envelope_obj = json.loads(envelope)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"A2A operation '{operation}' received invalid JSON envelope"
                ) from exc
        elif isinstance(envelope, Task):
            envelope_obj = {"task": envelope.model_dump(mode="json")}
        elif isinstance(envelope, Mapping):
            envelope_obj = dict(envelope)
        else:
            raise TypeError(
                f"A2A operation '{operation}' expects a mapping payload or JSON string"
            )

        if "task" not in envelope_obj:
            raise ValueError(
                f"A2A operation '{operation}' requires a 'task' entry in the payload"
            )

        task_value = envelope_obj["task"]
        if isinstance(task_value, str):
            try:
                task_value = json.loads(task_value)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"A2A operation '{operation}' received invalid JSON task payload"
                ) from exc
        elif isinstance(task_value, Task):
            task_value = task_value.model_dump(mode="json")

        if not isinstance(task_value, Mapping):
            raise TypeError(
                f"A2A operation '{operation}' requires the task to be a mapping"
            )

        envelope_obj["task"] = dict(task_value)
        return envelope_obj

    def _build_send_message_request(
        self,
        envelope: Mapping[str, Any],
        *,
        operation: str,
    ) -> dict[str, Any]:
        """Convert a task envelope into a JSON-RPC ``message/send`` request."""

        task_payload = envelope.get("task")
        try:
            task = Task.model_validate(task_payload)
        except ValidationError as exc:
            raise ValueError(
                f"A2A operation '{operation}' received an invalid task payload"
            ) from exc

        if not task.history:
            raise ValueError(
                f"A2A operation '{operation}' requires the task to include at least one message"
            )

        message = task.history[-1]
        params = MessageSendParams(
            message=message,
            metadata={"task": task.model_dump(mode="json")},
        )
        request = SendMessageRequest(id=self._request_id_factory(), params=params)
        return request.model_dump(mode="json")

    @staticmethod
    def _request_id_factory() -> str:
        """Generate a JSON-RPC request identifier."""

        return uuid4().hex


_CLIENT_SINGLETON: SalespersonA2AClient | None = None


def get_salesperson_a2a_client() -> SalespersonA2AClient:
    """Return a process-wide :class:`SalespersonA2AClient` singleton."""

    global _CLIENT_SINGLETON
    if _CLIENT_SINGLETON is None:
        card = get_payment_agent_card()
        if not card.url:
            raise RuntimeError("Payment agent card is missing the RPC URL")
        _CLIENT_SINGLETON = SalespersonA2AClient(base_url=card.url)
    return _CLIENT_SINGLETON


def set_salesperson_a2a_client(client: SalespersonA2AClient | None) -> None:
    """Inject or reset the singleton instance (useful for tests)."""

    global _CLIENT_SINGLETON
    _CLIENT_SINGLETON = client


__all__ = [
    "SalespersonA2AClient",
    "get_salesperson_a2a_client",
    "set_salesperson_a2a_client",
]

