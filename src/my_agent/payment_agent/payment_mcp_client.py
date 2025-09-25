"""Async helper for calling salesperson MCP tools over HTTP.

This module centralises the code that connects to the salesperson MCP server
so that other modules (such as :mod:`payment_tasks`) no longer import the
in-process tool implementations directly. Keeping the networking logic here
makes it easy to swap the transport in the future and gives us a clean seam
for unit tests.
"""

from __future__ import annotations

import json
from typing import Any

from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool.mcp_session_manager import MCPSessionManager

from config import MCP_PAYMENT_TOKEN, MCP_SERVER_HOST_PAYMENT, MCP_SERVER_PORT_PAYMENT
from my_agent.base_mcp_client import BaseMcpClient

mcp_sse_url = f"http://{MCP_SERVER_HOST_PAYMENT}:{MCP_SERVER_PORT_PAYMENT}/sse"
mcp_streamable_http_url = f"http://{MCP_SERVER_HOST_PAYMENT}:{MCP_SERVER_PORT_PAYMENT}/mcp"
class PaymentMcpClient(BaseMcpClient):
    """Small wrapper around :class:`MCPSessionManager` for payment tools."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        session_manager: MCPSessionManager | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            session_manager=session_manager,
            default_base_url=mcp_streamable_http_url,
            token=MCP_PAYMENT_TOKEN,
        )

    async def create_order(self, *, payload: dict[str, Any] | str) -> dict[str, Any]:
        """Create an order using the shared MCP payment tool."""
        if isinstance(payload, str):
            payload = json.loads(payload)

        if not isinstance(payload, dict):
            raise TypeError("create_order(payload=...) expects a dict or JSON string")

        response = await self._call_tool_json("create_order", {"payload": payload})
        data = self._extract_success_data(response, tool="create_order")
        if not isinstance(data, dict):
            raise RuntimeError(
                "MCP tool 'create_order' returned non-dict data payload"
            )
        return data

    async def query_order_status(self, *, payload: dict[str, Any] | str) -> dict[str, Any]:
        """Query order status using the shared MCP payment tool."""
        if isinstance(payload, str):
            payload = json.loads(payload)

        if not isinstance(payload, dict):
            raise TypeError("create_order(payload=...) expects a dict or JSON string")

        response = await self._call_tool_json("query_order_status", {"payload": payload})
        data = self._extract_success_data(response, tool="query_order_status")
        if not isinstance(data, dict):
            raise RuntimeError(
                "MCP tool 'query_order_status' returned non-dict data payload"
            )
        return data


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