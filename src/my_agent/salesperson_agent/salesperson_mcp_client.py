from __future__ import annotations

import logging
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
        logger: logging.Logger,
        session_manager: MCPSessionManager | None = None,
    ) -> None:
        super().__init__(
            logger=logger,
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

    async def get_current_user_id(self, *, context_id: str) -> dict[str, Any]:
        """
        Get the current authenticated user ID for the given context.

        Args:
            context_id: The payment context identifier

        Returns:
            user_id if found, None otherwise
        """
        payload = await self._call_tool_json(
            "get_current_user_id", {"context_id": context_id}
        )
        return self._ensure_response_format(payload, tool="get_current_user_id")

    async def authenticate_user(self, *, username: str, password: str) -> dict[str, Any]:
        """
        Authenticate user via MCP tool.

        Args:
            username: Username or email
            password: User password

        Returns:
            Response with access_token, user_id, username if successful
        """
        payload = await self._call_tool_json(
            "authenticate_user", {"username": username, "password": password}
        )
        return self._ensure_response_format(payload, tool="authenticate_user")


_client: SalespersonMcpClient | None = None


def get_salesperson_mcp_client() -> SalespersonMcpClient:
    from src.my_agent.salesperson_agent import salesperson_agent_logger
    global _client
    if _client is None:
        _client = SalespersonMcpClient(logger=salesperson_agent_logger)
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
prepare_search_product_documents_tool = FunctionTool(prepare_search_product_documents)