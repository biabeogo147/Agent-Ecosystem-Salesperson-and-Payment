from __future__ import annotations

import json
import uuid
import httpx
import logging
from typing import Any, Dict
from a2a.types import Message, MessageSendParams, Task

from src.utils.request_format_jsonrpc import RequestFormatJSONRPC


class BaseA2AClient:
    """Lightweight client for sending JSON-RPC ``message.send`` requests."""

    def __init__(
        self,
        *,
        base_url: str,
        client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
        endpoint_path: str = "/",
        logger: logging.Logger,
    ) -> None:
        self.logger = logger

        self._base_url = base_url
        self._endpoint_path = endpoint_path

        if client is None:
            self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)
            self._owns_client = True
        else:
            self._client = client
            self._owns_client = False

        self.logger.info("A2A client initialised (base_url=%s, path=%s, owns_client=%s)",
                         self._base_url, self._endpoint_path, self._owns_client)

    async def close(self) -> None:
        """Close the underlying HTTP client if this instance created it."""
        if self._owns_client:
            self.logger.debug("Closing owned HTTP client")
            await self._client.aclose()

    async def __aenter__(self) -> "BaseA2AClient":
        self.logger.debug("Entering A2A client context")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.logger.debug("Exiting A2A client context")
        await self.close()

    async def send_message(self, params: MessageSendParams) -> Message:
        """Send a pre-built ``MessageSendParams`` payload to the remote agent."""
        rid = str(uuid.uuid4())
        self.logger.debug("Building JSON-RPC request (id=%s)", rid)
        payload = RequestFormatJSONRPC(id=rid, params=params.model_dump(mode="json")).to_dict()
        self.logger.debug("Sending JSON-RPC request (payload=%s)", payload)

        self.logger.info("POST message.send (id=%s) -> %s%s", rid, self._base_url, self._endpoint_path)
        try:
            self.logger.debug("Sending JSON-RPC request (payload=%s)", payload)
            response = await self._client.post(self._endpoint_path, json=payload)
            self.logger.debug("Received HTTP response (playload=%s)", response.content)
        except httpx.RequestError as exc:
            self.logger.error("HTTP request failed (id=%s): %s", rid, exc)
            raise

        self.logger.info("Received HTTP %s for message.send (id=%s)", response.status_code, rid)

        try:
            body = response.json()
        except json.JSONDecodeError as exc:
            self.logger.warning("Non-JSON response from remote A2A agent (status=%s, id=%s)",
                                response.status_code, rid)
            raise RuntimeError("Remote A2A agent returned non-JSON response") from exc

        message_payload = self._extract_message_from_response(body, self.logger)
        message = Message.model_validate(message_payload)
        self.logger.info("Parsed Message successfully (id=%s, role=%s, parts=%d)",
                         rid, getattr(message, "role", None), len(getattr(message, "content", []) or []))
        return message

    async def send_task(
        self,
        payload: Dict[str, Any],
        *,
        metadata: Dict[str, Any] | None = None,
    ) -> Message:
        """Convenience wrapper that accepts a serialised task mapping."""
        self.logger.debug("send_task_payload called")
        task_payload = payload.get("task")
        if task_payload is None:
            self.logger.warning("send_task_payload missing 'task' entry")
            raise ValueError("Payload is missing the 'task' entry required by A2A")

        task = Task.model_validate(task_payload)
        if not task.history:
            self.logger.warning("send_task called with empty task history")
            raise ValueError("Task does not contain any messages to send")
        message = task.history[-1]

        skill_id = (task.metadata or {}).get("skill_id")
        if skill_id:
            self.logger.info("send_task dispatch (skill_id=%s)", skill_id)
        else:
            self.logger.debug("send_task dispatch without skill_id")

        metadata_payload = dict(metadata or {})
        metadata_payload["task"] = task.model_dump(mode="json")

        params = MessageSendParams(message=message, metadata=metadata_payload)
        return await self.send_message(params)

    @classmethod
    def _extract_message_from_response(cls, payload: Any, logger: logging.Logger) -> Any:
        if not isinstance(payload, dict):
            logger.warning("Non-object JSON-RPC response from remote agent")
            raise RuntimeError("Remote A2A agent returned a non-object JSON-RPC response")

        if "error" in payload:
            error_obj = payload["error"]
            if isinstance(error_obj, dict):
                code = error_obj.get("code")
                message = error_obj.get("message", "")
                detail = error_obj.get("data")
                logger.warning("JSON-RPC error (code=%s, message=%s)", code, message)
                detail_text = f" Details: {detail}" if detail is not None else ""
                raise RuntimeError(
                    f"Remote A2A agent returned JSON-RPC error {code}: {message}{detail_text}"
                )
            logger.warning("JSON-RPC error response (unstructured)")
            raise RuntimeError("Remote A2A agent returned JSON-RPC error response")

        result = payload.get("result")
        if result is None:
            logger.warning("JSON-RPC response missing 'result'")
            raise RuntimeError("Remote A2A agent response does not contain 'result'")

        return result