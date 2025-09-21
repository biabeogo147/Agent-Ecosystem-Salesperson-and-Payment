"""HTTP client for communicating with the MCP tool microservice."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from http.client import HTTPConnection, HTTPSConnection, HTTPResponse
from typing import Any, Mapping
from urllib.parse import urlparse

from my_mcp.api import MCPService


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

    async def list_tools(self) -> list[Mapping[str, Any]]:
        if self.transport is not None:
            status, body = await self.transport.list_tools()
            if status != 200:
                raise MCPServiceError("Failed to list tools", status_code=status, details=body)
            if not isinstance(body, list):
                raise MCPServiceError("Unexpected response payload", details=body)
            return body

        response = await asyncio.to_thread(self._request, "GET", "/v1/tools", None)
        return self._parse_json(response)

    async def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        if self.transport is not None:
            status, body = await self.transport.invoke_tool(name, arguments)
            if status != 200:
                raise MCPServiceError(
                    message=body.get("message", f"Tool '{name}' invocation failed.") if isinstance(body, Mapping) else str(body),
                    status_code=status,
                    details=body if isinstance(body, Mapping) else None,
                )
            if not isinstance(body, Mapping):
                raise MCPServiceError("Unexpected response payload", details=body)
            return body

        response = await asyncio.to_thread(
            self._request,
            "POST",
            f"/v1/tools/{name}:invoke",
            {"arguments": dict(arguments)},
        )
        payload = self._parse_json(response)
        if payload.get("status") != "success":
            raise MCPServiceError(
                message=payload.get("message", f"Tool '{name}' invocation failed."),
                status_code=response.status,
                details=payload,
            )
        return payload

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


__all__ = ["MCPServiceClient", "MCPServiceError"]
