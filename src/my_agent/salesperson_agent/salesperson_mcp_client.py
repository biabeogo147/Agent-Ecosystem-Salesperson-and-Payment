"""Async helper for calling salesperson MCP tools over HTTP.

This module centralises the code that connects to the salesperson MCP server
so that other modules (such as :mod:`payment_tasks`) no longer import the
in-process tool implementations directly. Keeping the networking logic here
makes it easy to swap the transport in the future and gives us a clean seam
for unit tests.
"""

from __future__ import annotations

from typing import Any, Dict

from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool.mcp_session_manager import MCPSessionManager

from config import MCP_SERVER_HOST_SALESPERSON, MCP_SERVER_PORT_SALESPERSON, MCP_SALESPERSON_TOKEN
from my_agent.base_mcp_client import BaseMcpClient

mcp_sse_url = f"http://{MCP_SERVER_HOST_SALESPERSON}:{MCP_SERVER_HOST_SALESPERSON}/sse"
mcp_streamable_http_url = f"http://{MCP_SERVER_HOST_SALESPERSON}:{MCP_SERVER_PORT_SALESPERSON}/mcp"


class SalespersonMcpClient(BaseMcpClient):
    """Small wrapper around :class:`MCPSessionManager` for salesperson tools."""

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
            token=MCP_SALESPERSON_TOKEN,
        )

    async def generate_correlation_id(self, *, prefix: str) -> str:
        """Request a new correlation ID from the MCP server."""
        payload = await self._call_tool_json(
            "generate_correlation_id", {"prefix": prefix}
        )
        data = self._extract_success_data(payload, tool="generate_correlation_id")
        if not isinstance(data, str):
            raise RuntimeError(
                "MCP tool 'generate_correlation_id' returned non-string data"
            )
        return data

    async def generate_return_url(self, correlation_id: str) -> str:
        """Request the return URL bound to ``correlation_id`` from MCP."""
        payload = await self._call_tool_json(
            "generate_return_url", {"correlation_id": correlation_id}
        )
        data = self._extract_success_data(payload, tool="generate_return_url")
        if not isinstance(data, str):
            raise RuntimeError(
                "MCP tool 'generate_return_url' returned non-string data"
            )
        return data

    async def generate_cancel_url(self, correlation_id: str) -> str:
        """Request the cancel URL bound to ``correlation_id`` from MCP."""
        payload = await self._call_tool_json(
            "generate_cancel_url", {"correlation_id": correlation_id}
        )
        data = self._extract_success_data(payload, tool="generate_cancel_url")
        if not isinstance(data, str):
            raise RuntimeError(
                "MCP tool 'generate_cancel_url' returned non-string data"
            )
        return data

    async def find_product(self, *, query: str) -> dict[str, Any]:
        """Look up products via the MCP ``find_product`` tool."""
        payload = await self._call_tool_json("find_product", {"query": query})
        return self._ensure_response_format(payload, tool="find_product")

    async def calc_shipping(self, *, weight: float, distance: float) -> dict[str, Any]:
        """Calculate shipping costs using the shared MCP shipping tool."""
        payload = await self._call_tool_json(
            "calc_shipping", {"weight": weight, "distance": distance}
        )
        return self._ensure_response_format(payload, tool="calc_shipping")

    async def reserve_stock(self, *, sku: str, quantity: int) -> dict[str, Any]:
        """Reserve inventory using the MCP stock management tool."""
        payload = await self._call_tool_json(
            "reserve_stock", {"sku": sku, "quantity": quantity}
        )
        return self._ensure_response_format(payload, tool="reserve_stock")


_client: SalespersonMcpClient | None = None


def get_salesperson_mcp_client() -> SalespersonMcpClient:
    """Return a process-wide :class:`SalespersonMcpClient` singleton."""
    global _client
    if _client is None:
        _client = SalespersonMcpClient()
    return _client


async def prepare_find_product(query: str) -> Dict[str, Any]:
    """Look up products via the salesperson MCP server."""
    client = get_salesperson_mcp_client()
    return await prepare_find_product_with_client(query=query, client=client)


async def prepare_calc_shipping(weight: float, distance: float) -> Dict[str, Any]:
    """Calculate shipping costs through the MCP shipping helper."""
    client = get_salesperson_mcp_client()
    return await prepare_calc_shipping_with_client(weight=weight, distance=distance, client=client)


async def prepare_reserve_stock(sku: str, quantity: int) -> Dict[str, Any]:
    """Reserve inventory through the MCP stock tool."""
    client = get_salesperson_mcp_client()
    return await prepare_reserve_stock_with_client(sku=sku, quantity=quantity, client=client)


async def prepare_find_product_with_client(query: str, client: SalespersonMcpClient) -> Dict[str, Any]:
    """Look up products via the salesperson MCP server."""
    return await client.find_product(query=query)


async def prepare_calc_shipping_with_client(weight: float, distance: float, client: SalespersonMcpClient) -> Dict[str, Any]:
    """Calculate shipping costs through the MCP shipping helper."""
    return await client.calc_shipping(weight=weight, distance=distance)


async def prepare_reserve_stock_with_client(sku: str, quantity: int, client: SalespersonMcpClient) -> Dict[str, Any]:
    """Reserve inventory through the MCP stock tool."""
    return await client.reserve_stock(sku=sku, quantity=quantity)


prepare_find_product_tool = FunctionTool(prepare_find_product)
prepare_calc_shipping_tool = FunctionTool(prepare_calc_shipping)
prepare_reserve_stock_tool = FunctionTool(prepare_reserve_stock)


__all__ = [
    "SalespersonMcpClient",
    "get_salesperson_mcp_client",
    "prepare_find_product",
    "prepare_calc_shipping",
    "prepare_reserve_stock",
    "prepare_find_product_with_client",
    "prepare_calc_shipping_with_client",
    "prepare_reserve_stock_with_client",
    "prepare_find_product_tool",
    "prepare_calc_shipping_tool",
    "prepare_reserve_stock_tool",
]