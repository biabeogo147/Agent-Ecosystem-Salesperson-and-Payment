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
    "prepare_find_product",
    "prepare_calc_shipping",
    "prepare_reserve_stock",
    "prepare_find_product_tool",
    "prepare_calc_shipping_tool",
    "prepare_reserve_stock_tool",
]
