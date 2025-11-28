from __future__ import annotations

import json
from typing import Any

from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool.mcp_session_manager import MCPSessionManager

from src.config import MCP_PAYMENT_TOKEN, MCP_SERVER_HOST_PAYMENT, MCP_SERVER_PORT_PAYMENT
from src.my_agent.base_mcp_client import BaseMcpClient
from src.utils.logger import get_current_logger

mcp_sse_url = f"http://{MCP_SERVER_HOST_PAYMENT}:{MCP_SERVER_PORT_PAYMENT}/sse"
mcp_streamable_http_url = f"http://{MCP_SERVER_HOST_PAYMENT}:{MCP_SERVER_PORT_PAYMENT}/mcp"


class PaymentMcpClient(BaseMcpClient):
    """Small wrapper around :class:`MCPSessionManager` for payment tools."""

    def __init__(
        self,
        *,
        session_manager: MCPSessionManager | None = None,
    ) -> None:
        super().__init__(
            base_url=mcp_streamable_http_url,
            token=MCP_PAYMENT_TOKEN,
            session_manager=session_manager,
        )

    async def create_order(self, *, payload: dict[str, Any] | str) -> dict[str, Any]:
        """Create an order using the shared MCP payment tool."""
        logger = get_current_logger()
        logger.debug(f"[PaymentMcpClient] create_order called with payload: {payload}")
        if isinstance(payload, str):
            payload = json.loads(payload)

        if not isinstance(payload, dict):
            raise TypeError("create_order(payload=...) expects a dict or JSON string")

        try:
            response = await self._call_tool_json("create_order", {"payload": payload})
            logger.debug(f"[PaymentMcpClient] create_order raw response: {response}")
            data = self._extract_success_data(response, tool="create_order")
            if not isinstance(data, dict):
                raise RuntimeError("MCP tool 'create_order' returned non-dict data payload")
            logger.info(f"[PaymentMcpClient] create_order success, order_id: {data.get('order_id')}")
            return data
        except Exception as e:
            logger.exception(f"[PaymentMcpClient] create_order failed")
            raise

    async def query_order_status(self, *, payload: dict[str, Any] | str) -> dict[str, Any]:
        """Query order status using the shared MCP payment tool."""
        logger = get_current_logger()
        logger.debug(f"[PaymentMcpClient] query_order_status called with payload: {payload}")
        if isinstance(payload, str):
            payload = json.loads(payload)

        if not isinstance(payload, dict):
            raise TypeError("query_order_status(payload=...) expects a dict or JSON string")

        try:
            response = await self._call_tool_json("query_order_status", {"payload": payload})
            logger.debug(f"[PaymentMcpClient] query_order_status raw response: {response}")
            data = self._extract_success_data(response, tool="query_order_status")
            if not isinstance(data, dict):
                raise RuntimeError("MCP tool 'query_order_status' returned non-dict data payload")
            logger.info(f"[PaymentMcpClient] query_order_status success")
            return data
        except Exception as e:
            logger.exception(f"[PaymentMcpClient] query_order_status failed")
            raise

    async def query_gateway_status(self, *, payload: dict[str, Any] | str) -> dict[str, Any]:
        """Query payment gateway for actual order status."""
        logger = get_current_logger()
        logger.debug(f"[PaymentMcpClient] query_gateway_status called with payload: {payload}")
        if isinstance(payload, str):
            payload = json.loads(payload)

        if not isinstance(payload, dict):
            raise TypeError("query_gateway_status(payload=...) expects a dict or JSON string")

        try:
            response = await self._call_tool_json("query_gateway_status", {"payload": payload})
            logger.debug(f"[PaymentMcpClient] query_gateway_status raw response: {response}")
            data = self._extract_success_data(response, tool="query_gateway_status")
            if not isinstance(data, dict):
                raise RuntimeError("MCP tool 'query_gateway_status' returned non-dict data payload")
            logger.info(f"[PaymentMcpClient] query_gateway_status success")
            return data
        except Exception as e:
            logger.exception(f"[PaymentMcpClient] query_gateway_status failed")
            raise


_client: PaymentMcpClient | None = None


def get_payment_mcp_client() -> PaymentMcpClient:
    """Return a process-wide :class:`PaymentMcpClient` singleton."""
    global _client
    if _client is None:
        _client = PaymentMcpClient()
    return _client


# TODO: define detail params instead of generic payload
async def create_order(payload: dict[str, Any]) -> dict[str, Any]:
    """Create an order using the shared MCP payment tool."""
    client = get_payment_mcp_client()
    return await client.create_order(payload=payload)


async def query_order_status(payload: dict[str, Any]) -> dict[str, Any]:
    """Query order status using the shared MCP payment tool."""
    client = get_payment_mcp_client()
    return await client.query_order_status(payload=payload)


async def query_gateway_status(payload: dict[str, Any]) -> dict[str, Any]:
    """Query payment gateway for actual order status."""
    client = get_payment_mcp_client()
    return await client.query_gateway_status(payload=payload)


create_order_tool = FunctionTool(create_order)
query_order_status_tool = FunctionTool(query_order_status)
query_gateway_status_tool = FunctionTool(query_gateway_status)