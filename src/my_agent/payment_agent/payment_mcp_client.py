from __future__ import annotations

import json
from typing import Any

from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool.mcp_session_manager import MCPSessionManager

from src.config import MCP_PAYMENT_TOKEN, MCP_SERVER_HOST_PAYMENT, MCP_SERVER_PORT_PAYMENT
from src.my_agent.base_mcp_client import BaseMcpClient

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
            raise RuntimeError("MCP tool 'create_order' returned non-dict data payload")
        return data

    async def query_order_status(self, *, payload: dict[str, Any] | str) -> dict[str, Any]:
        """Query order status using the shared MCP payment tool."""
        if isinstance(payload, str):
            payload = json.loads(payload)

        if not isinstance(payload, dict):
            raise TypeError("query_order_status(payload=...) expects a dict or JSON string")

        response = await self._call_tool_json("query_order_status", {"payload": payload})
        data = self._extract_success_data(response, tool="query_order_status")
        if not isinstance(data, dict):
            raise RuntimeError("MCP tool 'query_order_status' returned non-dict data payload")
        return data

    async def update_order_status(self, *, payload: dict[str, Any] | str) -> dict[str, Any]:
        """Update order status using the shared MCP payment tool."""
        if isinstance(payload, str):
            payload = json.loads(payload)

        if not isinstance(payload, dict):
            raise TypeError("update_order_status(payload=...) expects a dict or JSON string")

        response = await self._call_tool_json("update_order_status", {"payload": payload})
        data = self._extract_success_data(response, tool="update_order_status")
        if not isinstance(data, dict):
            raise RuntimeError("MCP tool 'update_order_status' returned non-dict data payload")
        return data

    async def query_gateway_status(self, *, payload: dict[str, Any] | str) -> dict[str, Any]:
        """Query payment gateway for actual order status."""
        if isinstance(payload, str):
            payload = json.loads(payload)

        if not isinstance(payload, dict):
            raise TypeError("query_gateway_status(payload=...) expects a dict or JSON string")

        response = await self._call_tool_json("query_gateway_status", {"payload": payload})
        data = self._extract_success_data(response, tool="query_gateway_status")
        if not isinstance(data, dict):
            raise RuntimeError("MCP tool 'query_gateway_status' returned non-dict data payload")
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


async def update_order_status(payload: dict[str, Any]) -> dict[str, Any]:
    """Update order status using the shared MCP payment tool."""
    client = get_payment_mcp_client()
    return await client.update_order_status(payload=payload)


async def query_gateway_status(payload: dict[str, Any]) -> dict[str, Any]:
    """Query payment gateway for actual order status."""
    client = get_payment_mcp_client()
    return await client.query_gateway_status(payload=payload)


create_order_tool = FunctionTool(create_order)
query_order_status_tool = FunctionTool(query_order_status)
update_order_status_tool = FunctionTool(update_order_status)
query_gateway_status_tool = FunctionTool(query_gateway_status)