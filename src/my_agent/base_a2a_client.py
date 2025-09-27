"""Shared HTTP helpers for talking to remote A2A agents.

The payment flow currently ships with a dedicated :class:`SalespersonA2AClient`
but a number of other agents will eventually need to speak the same JSON-RPC
protocol.  This module hosts a small, well-tested base class that understands
how to serialise :class:`~a2a.types.Task` objects into ``message.send`` calls and
how to parse the structured :mod:`utils.response_format` responses returned by
the server.

Keeping the networking code here allows individual agents to focus on their
business logic while still benefitting from the same error handling and
transport behaviour.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Mapping

import httpx
from a2a.types import Message, MessageSendParams, Task

from utils.status import Status


class BaseA2AClient:
    """Lightweight client for sending JSON-RPC ``message.send`` requests."""

    def __init__(
        self,
        *,
        base_url: str,
        client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
        endpoint_path: str = "/",
    ) -> None:
        self._base_url = base_url
        self._endpoint_path = endpoint_path
        if client is None:
            self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)
            self._owns_client = True
        else:
            self._client = client
            self._owns_client = False

    async def close(self) -> None:
        """Close the underlying HTTP client if this instance created it."""

        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "BaseA2AClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def send_message(
        self,
        params: MessageSendParams,
        *,
        request_id: str | None = None,
    ) -> Message:
        """Send a pre-built ``MessageSendParams`` payload to the remote agent."""

        payload = self._build_json_rpc_request(params, request_id=request_id)
        response = await self._client.post(self._endpoint_path, json=payload)
        response.raise_for_status()
        try:
            body = response.json()
        except json.JSONDecodeError as exc:  # pragma: no cover - httpx guards well
            raise RuntimeError("Remote A2A agent returned non-JSON response") from exc
        message_payload = self._extract_message_from_response(body)
        return Message.model_validate(message_payload)

    async def send_task(
        self,
        task: Task,
        *,
        metadata: Mapping[str, Any] | None = None,
        request_id: str | None = None,
        message: Message | None = None,
    ) -> Message:
        """Send the last message associated with ``task`` to the remote agent."""

        if message is None:
            if not task.history:
                raise ValueError("Task does not contain any messages to send")
            message = task.history[-1]

        metadata_payload = dict(metadata or {})
        metadata_payload.setdefault("task", task.model_dump(mode="json"))

        params = MessageSendParams(message=message, metadata=metadata_payload)
        return await self.send_message(params, request_id=request_id)

    async def send_task_payload(
        self,
        payload: Mapping[str, Any],
        *,
        metadata: Mapping[str, Any] | None = None,
        request_id: str | None = None,
    ) -> Message:
        """Convenience wrapper that accepts a serialised task mapping."""

        task_payload = payload.get("task")
        if task_payload is None:
            raise ValueError("Payload is missing the 'task' entry required by A2A")

        task = Task.model_validate(task_payload)
        return await self.send_task(
            task,
            metadata=metadata,
            request_id=request_id,
        )

    def _build_json_rpc_request(
        self,
        params: MessageSendParams,
        *,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id or str(uuid.uuid4()),
            "method": "message.send",
            "params": params.model_dump(mode="json"),
        }

    @staticmethod
    def _ensure_response_format(payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise RuntimeError(
                "Remote A2A agent returned a malformed JSON-RPC result payload",
            )

        missing = [key for key in ("status", "message", "data") if key not in payload]
        if missing:
            raise RuntimeError(
                "Remote A2A agent returned ResponseFormat missing keys: " + ", ".join(missing)
            )

        return payload

    @classmethod
    def _extract_success_data(cls, payload: Any) -> Any:
        response = cls._ensure_response_format(payload)
        status = response.get("status")
        if status != Status.SUCCESS.value:
            message = response.get("message", "")
            raise RuntimeError(
                f"Remote A2A agent returned status '{status}': {message}"
            )
        return response.get("data")

    @classmethod
    def _extract_message_from_response(cls, payload: Any) -> Any:
        if not isinstance(payload, dict):
            raise RuntimeError("Remote A2A agent returned a non-object JSON-RPC response")

        if "error" in payload:
            error_obj = payload["error"]
            if isinstance(error_obj, dict):
                code = error_obj.get("code")
                message = error_obj.get("message", "")
                detail = error_obj.get("data")
                detail_text = f" Details: {detail}" if detail is not None else ""
                raise RuntimeError(
                    f"Remote A2A agent returned JSON-RPC error {code}: {message}{detail_text}"
                )
            raise RuntimeError("Remote A2A agent returned JSON-RPC error response")

        result = payload.get("result")
        if result is None:
            raise RuntimeError("Remote A2A agent response does not contain 'result'")

        data = cls._extract_success_data(result)
        if not isinstance(data, dict):
            raise RuntimeError(
                "Remote A2A agent ResponseFormat 'data' entry must be a mapping"
            )
        return data


__all__ = ["BaseA2AClient"]
