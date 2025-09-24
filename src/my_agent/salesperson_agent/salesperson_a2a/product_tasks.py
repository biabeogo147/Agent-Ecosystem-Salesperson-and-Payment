"""Wrappers for product-related salesperson MCP tools.

These helpers keep the catalogue, shipping, and inventory interactions in one
place and make it easy to swap in fake MCP clients during tests.  Each
function returns the parsed JSON payload produced by the upstream MCP server
so callers receive a ``dict`` that mirrors the ``ResponseFormat`` schema.
"""

from __future__ import annotations

from typing import Any, Dict

from google.adk.tools import FunctionTool

from my_agent.salesperson_agent.salesperson_mcp_client import (
    SalespersonMcpClient,
    get_salesperson_mcp_client,
)

ResponseDict = Dict[str, Any]


async def find_product(
    query: str, *, mcp_client: SalespersonMcpClient | None = None
) -> ResponseDict:
    """Look up products via the salesperson MCP server."""
    client = mcp_client or get_salesperson_mcp_client()
    return await client.find_product(query=query)


async def calc_shipping(
    weight: float,
    distance: float,
    *,
    mcp_client: SalespersonMcpClient | None = None,
) -> ResponseDict:
    """Calculate shipping costs through the MCP shipping helper."""
    client = mcp_client or get_salesperson_mcp_client()
    return await client.calc_shipping(weight=weight, distance=distance)


async def reserve_stock(
    sku: str,
    quantity: int,
    *,
    mcp_client: SalespersonMcpClient | None = None,
) -> ResponseDict:
    """Reserve inventory through the MCP stock tool."""
    client = mcp_client or get_salesperson_mcp_client()
    return await client.reserve_stock(sku=sku, quantity=quantity)


find_product_tool = FunctionTool(find_product)
calc_shipping_tool = FunctionTool(calc_shipping)
reserve_stock_tool = FunctionTool(reserve_stock)


__all__ = [
    "ResponseDict",
    "find_product",
    "calc_shipping",
    "reserve_stock",
    "find_product_tool",
    "calc_shipping_tool",
    "reserve_stock_tool",
]
