"""Async helper for calling salesperson MCP tools over HTTP.

This module centralises the code that connects to the salesperson MCP server
so that other modules (such as :mod:`payment_tasks`) no longer import the
in-process tool implementations directly. Keeping the networking logic here
makes it easy to swap the transport in the future and gives us a clean seam
for unit tests.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from google.adk.tools import FunctionTool
from mcp import types as mcp_types
from google.adk.tools.mcp_tool.mcp_session_manager import MCPSessionManager

from my_mcp.mcp_connect_params import get_mcp_streamable_http_connect_params
from config import MCP_PAYMENT_TOKEN, MCP_SERVER_HOST_PAYMENT, MCP_SERVER_PORT_PAYMENT

mcp_sse_url = f"http://{MCP_SERVER_HOST_PAYMENT}:{MCP_SERVER_PORT_PAYMENT}/sse"
mcp_streamable_http_url = f"http://{MCP_SERVER_HOST_PAYMENT}:{MCP_SERVER_PORT_PAYMENT}/mcp"


class PaymentMcpClient:
    """Small wrapper around :class:`MCPSessionManager` for payment tools."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        session_manager: MCPSessionManager | None = None,
    ) -> None:
        self._base_url = base_url or mcp_streamable_http_url
        self._session_manager = session_manager or MCPSessionManager(
            get_mcp_streamable_http_connect_params(self._base_url, MCP_PAYMENT_TOKEN)
        )

    async def _call_tool(
        self, name: str, arguments: Optional[dict[str, Any]] = None
    ) -> mcp_types.CallToolResult:
        session = await self._session_manager.create_session()
        result = await session.call_tool(name, arguments)
        if result.isError:
            raise RuntimeError(
                f"MCP tool '{name}' returned an error payload: {result}"
            )
        return result

    async def _call_tool_text(
        self, name: str, arguments: Optional[dict[str, Any]] = None
    ) -> str:
        result = await self._call_tool(name, arguments)
        for part in result.content:
            if isinstance(part, mcp_types.TextContent):
                return part.text
        if result.structuredContent is not None:
            return json.dumps(result.structuredContent)
        raise RuntimeError(
            f"MCP tool '{name}' returned no textual content to interpret."
        )

    async def _call_tool_json(
        self, name: str, arguments: Optional[dict[str, Any]] = None
    ) -> Any:
        """Call a tool and interpret its response as JSON-compatible data."""
        result = await self._call_tool(name, arguments)
        if result.structuredContent is not None:
            return result.structuredContent

        for part in result.content:
            if isinstance(part, mcp_types.TextContent):
                if not part.text.strip():
                    continue
                try:
                    return json.loads(part.text)
                except json.JSONDecodeError as exc:
                    snippet = part.text[:200]
                    raise RuntimeError(
                        f"MCP tool '{name}' returned non-JSON text: {snippet}"
                    ) from exc

        raise RuntimeError(
            f"MCP tool '{name}' returned no JSON content to interpret."
        )

    async def create_order(self, *, payload: dict[str, Any] | str) -> dict[str, Any]:
        """Create an order using the shared MCP payment tool."""
        if isinstance(payload, str):
            payload = json.loads(payload)

        if not isinstance(payload, dict):
            raise TypeError("create_order(payload=...) expects a dict or JSON string")

        payload = await self._call_tool_json("create_order", {"payload": payload})
        if not isinstance(payload, dict):
            raise RuntimeError(
                "MCP tool 'create_order' returned an unexpected payload type"
            )
        return payload

    async def query_order_status(self, *, payload: dict[str, Any] | str) -> dict[str, Any]:
        """Query order status using the shared MCP payment tool."""
        if isinstance(payload, str):
            payload = json.loads(payload)

        if not isinstance(payload, dict):
            raise TypeError("create_order(payload=...) expects a dict or JSON string")

        payload = await self._call_tool_json("query_order_status", {"payload": payload})
        if not isinstance(payload, dict):
            raise RuntimeError(
                "MCP tool 'query_order_status' returned an unexpected payload type"
            )
        return payload


_client: PaymentMcpClient | None = None


def get_payment_mcp_client() -> PaymentMcpClient:
    """Return a process-wide :class:`PaymentMcpClient` singleton."""
    global _client
    if _client is None:
        _client = PaymentMcpClient()
    return _client


async def create_order(payload: dict[str, Any]) -> dict[str, Any]:
    """Create an order using the shared MCP payment tool."""
    client = get_payment_mcp_client()
    return await client.create_order(payload=payload)


async def query_order_status(payload: dict[str, Any]) -> dict[str, Any]:
    """Query order status using the shared MCP payment tool."""
    client = get_payment_mcp_client()
    return await client.query_order_status(payload=payload)


create_order_tool = FunctionTool(create_order)
query_order_status_tool = FunctionTool(query_order_status)


__all__ = [
    "PaymentMcpClient",
    "get_payment_mcp_client",
    "create_order",
    "query_order_status",
    "create_order_tool",
    "query_order_status_tool",
]