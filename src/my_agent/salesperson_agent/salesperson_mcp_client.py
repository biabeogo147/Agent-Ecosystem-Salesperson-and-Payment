from __future__ import annotations

from typing import Any, Dict

from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool.mcp_session_manager import MCPSessionManager

from src.config import MCP_SERVER_HOST_SALESPERSON, MCP_SERVER_PORT_SALESPERSON, MCP_SALESPERSON_TOKEN
from src.my_agent.base_mcp_client import BaseMcpClient

mcp_sse_url = f"http://{MCP_SERVER_HOST_SALESPERSON}:{MCP_SERVER_PORT_SALESPERSON}/sse"
mcp_streamable_http_url = f"http://{MCP_SERVER_HOST_SALESPERSON}:{MCP_SERVER_PORT_SALESPERSON}/mcp"


class SalespersonMcpClient(BaseMcpClient):
    def __init__(
        self,
        *,
        session_manager: MCPSessionManager | None = None,
    ) -> None:
        super().__init__(
            base_url=mcp_streamable_http_url,
            token=MCP_SALESPERSON_TOKEN,
            session_manager=session_manager,
        )

    async def generate_context_id(self, *, prefix: str) -> str:
        """Request a new context_id from the MCP server."""
        payload = await self._call_tool_json("generate_context_id", {"prefix": prefix})
        data = self._extract_success_data(payload, tool="generate_context_id")
        if not isinstance(data, str):
            raise RuntimeError("MCP tool 'generate_context_id' returned non-string data")
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

    async def search_product_documents(self, *, query: str, product_sku: str | None = None, limit: int = 5) -> dict[str, Any]:
        """Search product documents via the MCP ``search_product_documents`` tool."""
        payload = await self._call_tool_json(
            "search_product_documents", {"query": query, "product_sku": product_sku, "limit": limit}
        )
        return self._ensure_response_format(payload, tool="search_product_documents")


_client: SalespersonMcpClient | None = None


def get_salesperson_mcp_client() -> SalespersonMcpClient:
    global _client
    if _client is None:
        _client = SalespersonMcpClient()
    return _client


async def prepare_find_product(query: str) -> Dict[str, Any]:
    client = get_salesperson_mcp_client()
    return await client.find_product(query=query)


async def prepare_calc_shipping(weight: float, distance: float) -> Dict[str, Any]:
    client = get_salesperson_mcp_client()
    return await client.calc_shipping(weight=weight, distance=distance)


async def prepare_reserve_stock(sku: str, quantity: int) -> Dict[str, Any]:
    client = get_salesperson_mcp_client()
    return await client.reserve_stock(sku=sku, quantity=quantity)


async def prepare_search_product_documents(query: str) -> Dict[str, Any]:
    client = get_salesperson_mcp_client()
    return await client.search_product_documents(query=query)


prepare_find_product_tool = FunctionTool(prepare_find_product)
prepare_calc_shipping_tool = FunctionTool(prepare_calc_shipping)
prepare_reserve_stock_tool = FunctionTool(prepare_reserve_stock)
prepare_search_product_documents_tool = FunctionTool(prepare_search_product_documents)