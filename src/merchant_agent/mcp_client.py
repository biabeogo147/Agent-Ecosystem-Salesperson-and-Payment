"""HTTP client for communicating with the MCP tool microservice."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from http.client import HTTPConnection, HTTPSConnection, HTTPResponse
from typing import Any, Mapping
from urllib.parse import urlparse

from my_mcp.service import MCPService
from utils.status import Status
from utils.urls import MCP_URLS


class MCPServiceError(RuntimeError):
    """Raised when the MCP service cannot fulfil a request."""

    def __init__(self, message: str, *, status_code: int | None = None, details: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


@dataclass
class MCPServiceClient:
    """Minimal HTTP client with optional in-memory transport for tests."""

    base_url: str | None = None
    timeout: float = float(os.environ.get("MCP_SERVICE_TIMEOUT", "10"))
    transport: MCPService | None = None

    def __post_init__(self) -> None:
        self.base_url = (self.base_url or os.environ.get("MCP_SERVICE_URL") or "http://localhost:8000").rstrip("/")
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("MCP_SERVICE_URL must be an HTTP or HTTPS URL")
        self._scheme = parsed.scheme
        self._host = parsed.hostname or "localhost"
        default_port = 443 if self._scheme == "https" else 80
        self._port = parsed.port or default_port
        self._base_path = parsed.path.rstrip("/")
        if self._base_path and not self._base_path.startswith("/"):
            self._base_path = f"/{self._base_path}"
        self._list_tools_path = MCP_URLS.list_tools
        self._invoke_path_template = MCP_URLS.tool_invoke
        ws_scheme = "wss" if self._scheme == "https" else "ws"
        ws_path = f"{self._base_path}{MCP_URLS.websocket}" if self._base_path else MCP_URLS.websocket
        if (self._scheme == "http" and self._port != 80) or (self._scheme == "https" and self._port != 443):
            self._websocket_url = f"{ws_scheme}://{self._host}:{self._port}{ws_path}"
        else:
            self._websocket_url = f"{ws_scheme}://{self._host}{ws_path}"

    async def list_tools(self) -> list[Mapping[str, Any]]:
        if self.transport is not None:
            status, body = await self.transport.list_tools()
            payload = self._ensure_response_format(body)
            if status != 200:
                raise MCPServiceError(
                    "Failed to list tools",
                    status_code=status,
                    details=payload,
                )
            if payload.get("status") != Status.SUCCESS.value:
                raise MCPServiceError(
                    message=payload.get("message", "Tool registry request failed."),
                    details=payload,
                )
            data = payload.get("data")
            if not isinstance(data, list):
                raise MCPServiceError("Unexpected response payload", details=payload)
            return data

        response = await asyncio.to_thread(self._request, "GET", self._list_tools_path, None)
        payload = self._parse_json(response)
        body = self._ensure_response_format(payload)
        if body.get("status") != Status.SUCCESS.value:
            raise MCPServiceError(
                message=body.get("message", "Tool registry request failed."),
                details=body,
            )
        data = body.get("data")
        if not isinstance(data, list):
            raise MCPServiceError("Unexpected response payload", details=body)
        return data

    async def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        if self.transport is not None:
            status, body = await self.transport.invoke_tool(name, arguments)
            payload = self._ensure_response_format(body)
            if status != 200:
                raise MCPServiceError(
                    message=payload.get("message", f"Tool '{name}' invocation failed."),
                    status_code=status,
                    details=payload,
                )
            return payload

        response = await asyncio.to_thread(
            self._request,
            "POST",
            self._invoke_path_template.format(tool_name=name),
            {"arguments": dict(arguments)},
        )
        payload = self._parse_json(response)
        body = self._ensure_response_format(payload)
        return body

    def _request(self, method: str, path: str, body: Mapping[str, Any] | None) -> HTTPResponse:
        connection_cls = HTTPSConnection if self._scheme == "https" else HTTPConnection
        connection = connection_cls(self._host, self._port, timeout=self.timeout)
        try:
            full_path = f"{self._base_path}{path}" if self._base_path else path
            encoded_body = json.dumps(body).encode("utf-8") if body is not None else None
            headers = {"Content-Type": "application/json"}
            connection.request(method, full_path, body=encoded_body, headers=headers)
            response = connection.getresponse()
            if response.status >= 400:
                payload = self._parse_json(response)
                raise MCPServiceError(
                    message=payload.get("message", f"HTTP {response.status} error"),
                    status_code=response.status,
                    details=payload,
                )
            return response
        finally:
            connection.close()

    def _parse_json(self, response: HTTPResponse) -> Any:
        raw = response.read()
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:  # pragma: no cover - defensive safeguard
            raise MCPServiceError("Received invalid JSON from MCP service", details={"raw": raw.decode("utf-8", "ignore")}) from exc

    def _ensure_response_format(self, payload: Any) -> Mapping[str, Any]:
        if not isinstance(payload, Mapping):
            raise MCPServiceError("Unexpected response payload", details=payload)
        if "status" not in payload or "message" not in payload:
            raise MCPServiceError("Response payload missing required fields", details=payload)
        return payload

    @property
    def websocket_url(self) -> str:
        """Return the WebSocket endpoint derived from the configured base URL."""

        return self._websocket_url


__all__ = ["MCPServiceClient", "MCPServiceError"]
