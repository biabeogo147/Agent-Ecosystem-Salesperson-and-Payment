"""WebSocket client for communicating with the MCP tool microservice."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import json
import os
import ssl
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlparse

from my_mcp.service import MCPService
from utils.status import Status
from my_mcp.urls import MCP_URLS


class MCPServiceError(RuntimeError):
    """Raised when the MCP service cannot fulfil a request."""

    def __init__(self, message: str, *, status_code: int | None = None, details: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


@dataclass
class MCPServiceClient:
    """Minimal WebSocket client with optional in-memory transport for tests."""

    base_url: str | None = None
    timeout: float = float(os.environ.get("MCP_SERVICE_TIMEOUT", "10"))
    transport: MCPService | None = None

    def __post_init__(self) -> None:
        self.base_url = (self.base_url or os.environ.get("MCP_SERVICE_URL") or "http://localhost:8000").rstrip("/")
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("MCP_SERVICE_URL must be an HTTP or HTTPS URL")
        scheme = parsed.scheme
        host = parsed.hostname or "localhost"
        default_port = 443 if scheme == "https" else 80
        port = parsed.port or default_port
        base_path = parsed.path.rstrip("/")
        if base_path and not base_path.startswith("/"):
            base_path = f"/{base_path}"
        ws_scheme = "wss" if scheme == "https" else "ws"
        ws_path = f"{base_path}{MCP_URLS.websocket}" if base_path else MCP_URLS.websocket
        if (scheme == "http" and port != 80) or (scheme == "https" and port != 443):
            self._websocket_url = f"{ws_scheme}://{host}:{port}{ws_path}"
            self._host_header = f"{host}:{port}"
        else:
            self._websocket_url = f"{ws_scheme}://{host}{ws_path}"
            self._host_header = host
        self._scheme = scheme
        self._host = host
        self._port = port
        self._websocket_path = ws_path

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

        status_code, payload = await self._send_websocket_request({"action": "list_tools"})
        body = self._ensure_response_format(payload)
        if status_code != 200:
            raise MCPServiceError(
                "Failed to list tools",
                status_code=status_code,
                details=body,
            )
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

        status_code, payload = await self._send_websocket_request(
            {
                "action": "invoke_tool",
                "name": name,
                "arguments": dict(arguments),
            }
        )
        body = self._ensure_response_format(payload)
        if status_code != 200:
            raise MCPServiceError(
                message=body.get("message", f"Tool '{name}' invocation failed."),
                status_code=status_code,
                details=body,
            )
        return body

    async def _send_websocket_request(self, message: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
        response_raw = await self._perform_websocket_exchange(dict(message))

        try:
            envelope = json.loads(response_raw)
        except json.JSONDecodeError as exc:
            raise MCPServiceError(
                "Received invalid JSON from MCP WebSocket",
                details={"raw": response_raw},
            ) from exc

        if not isinstance(envelope, Mapping):
            raise MCPServiceError("Unexpected WebSocket response", details={"envelope": envelope})

        status_code = envelope.get("status_code")
        body = envelope.get("body")
        if not isinstance(status_code, int):
            raise MCPServiceError("WebSocket response missing status_code", details=envelope)
        if not isinstance(body, Mapping):
            raise MCPServiceError("WebSocket response missing body", details=envelope)

        return status_code, dict(body)

    async def _perform_websocket_exchange(self, message: Mapping[str, Any]) -> str:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    self._host,
                    self._port,
                    ssl=self._build_ssl_context(),
                ),
                timeout=self.timeout,
            )
        except (OSError, asyncio.TimeoutError) as exc:
            raise MCPServiceError(
                f"Unable to open WebSocket connection to {self._host}:{self._port}",
                details={"url": self._websocket_url},
            ) from exc

        try:
            key = base64.b64encode(os.urandom(16)).decode("ascii")
            handshake = (
                f"GET {self._websocket_path} HTTP/1.1\r\n"
                f"Host: {self._host_header}\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                "Sec-WebSocket-Version: 13\r\n\r\n"
            )
            writer.write(handshake.encode("ascii"))
            await writer.drain()

            status_line = await asyncio.wait_for(reader.readline(), timeout=self.timeout)
            if not status_line.startswith(b"HTTP/1.1 101"):
                raise MCPServiceError(
                    "WebSocket handshake failed",
                    details={"status_line": status_line.decode("latin-1").strip()},
                )

            headers: dict[str, str] = {}
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=self.timeout)
                if line in {b"\r\n", b""}:
                    break
                decoded = line.decode("latin-1").strip()
                if not decoded or ":" not in decoded:
                    continue
                name, value = decoded.split(":", 1)
                headers[name.lower()] = value.strip()

            accept_token = headers.get("sec-websocket-accept")
            expected_accept = base64.b64encode(
                hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
            ).decode("ascii")
            if accept_token != expected_accept:
                raise MCPServiceError(
                    "Invalid WebSocket handshake response",
                    details={"expected": expected_accept, "received": accept_token},
                )

            payload = json.dumps(message).encode("utf-8")
            mask = os.urandom(4)
            frame = bytearray()
            frame.append(0x81)
            length = len(payload)
            if length < 126:
                frame.append(0x80 | length)
            elif length < 65536:
                frame.append(0x80 | 126)
                frame.extend(length.to_bytes(2, "big"))
            else:
                frame.append(0x80 | 127)
                frame.extend(length.to_bytes(8, "big"))
            frame.extend(mask)
            frame.extend(b ^ mask[i % 4] for i, b in enumerate(payload))
            writer.write(frame)
            await writer.drain()

            first_two = await asyncio.wait_for(reader.readexactly(2), timeout=self.timeout)
            opcode = first_two[0] & 0x0F
            masked = first_two[1] & 0x80
            length = first_two[1] & 0x7F
            if length == 126:
                length = int.from_bytes(await asyncio.wait_for(reader.readexactly(2), timeout=self.timeout), "big")
            elif length == 127:
                length = int.from_bytes(await asyncio.wait_for(reader.readexactly(8), timeout=self.timeout), "big")
            mask_key = b""
            if masked:
                mask_key = await asyncio.wait_for(reader.readexactly(4), timeout=self.timeout)
            data = await asyncio.wait_for(reader.readexactly(length), timeout=self.timeout)
            if masked and mask_key:
                data = bytes(b ^ mask_key[i % 4] for i, b in enumerate(data))

            if opcode == 0x8:
                raise MCPServiceError("WebSocket connection closed by server")
            if opcode != 0x1:
                raise MCPServiceError("Unexpected WebSocket frame received", details={"opcode": opcode})

            response_text = data.decode("utf-8")

            close_frame = bytes([0x88, 0x00])
            writer.write(close_frame)
            await writer.drain()
            return response_text
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

    def _build_ssl_context(self) -> ssl.SSLContext | None:
        if self._scheme != "https":
            return None
        context = ssl.create_default_context()
        return context

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
