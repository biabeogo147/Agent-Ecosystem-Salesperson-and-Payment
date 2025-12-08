from __future__ import annotations

import logging
from typing import Any, Optional

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
        logger: logging.Logger,
        session_manager: MCPSessionManager | None = None,
    ) -> None:
        super().__init__(
            logger=logger,
            base_url=mcp_streamable_http_url,
            token=MCP_PAYMENT_TOKEN,
            session_manager=session_manager,
        )

    async def create_order(
        self,
        *,
        context_id: str,
        items: list[dict[str, Any]],
        channel: str,
        customer_name: str = "",
        customer_email: str = "",
        customer_phone: str = "",
        customer_shipping_address: str = "",
        note: str = "",
        user_id: Optional[int] = None,
        conversation_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Create an order using the shared MCP payment tool."""
        self._logger.debug(
            f"[PaymentMcpClient] create_order called: context_id={context_id}, "
            f"items_count={len(items)}, channel={channel}"
        )

        try:
            params = {
                "context_id": context_id,
                "items": items,
                "channel": channel,
                "customer_name": customer_name,
                "customer_email": customer_email,
                "customer_phone": customer_phone,
                "customer_shipping_address": customer_shipping_address,
                "note": note,
            }
            if user_id is not None:
                params["user_id"] = user_id
            if conversation_id is not None:
                params["conversation_id"] = conversation_id

            response = await self._call_tool_json("create_order", params)
            self._logger.debug(f"[PaymentMcpClient] create_order raw response: {response}")
            data = self._extract_success_data(response, tool="create_order")
            if not isinstance(data, dict):
                raise RuntimeError("MCP tool 'create_order' returned non-dict data payload")
            self._logger.info(f"[PaymentMcpClient] create_order success, order_id: {data.get('order_id')}")
            return data
        except Exception as e:
            self._logger.exception(f"[PaymentMcpClient] create_order failed")
            raise

    async def query_order_status(
        self,
        *,
        context_id: str,
        order_id: Optional[int] = None
    ) -> dict[str, Any]:
        """Query order status using the shared MCP payment tool."""
        self._logger.debug(f"[PaymentMcpClient] query_order_status called: context_id={context_id}, order_id={order_id}")

        try:
            params = {"context_id": context_id}
            if order_id is not None:
                params["order_id"] = order_id

            response = await self._call_tool_json("query_order_status", params)
            self._logger.debug(f"[PaymentMcpClient] query_order_status raw response: {response}")
            data = self._extract_success_data(response, tool="query_order_status")
            if not isinstance(data, dict):
                raise RuntimeError("MCP tool 'query_order_status' returned non-dict data payload")
            self._logger.info(f"[PaymentMcpClient] query_order_status success")
            return data
        except Exception as e:
            self._logger.exception(f"[PaymentMcpClient] query_order_status failed")
            raise

    async def query_gateway_status(self, *, order_id: int) -> dict[str, Any]:
        """Query payment gateway for actual order status."""
        self._logger.debug(f"[PaymentMcpClient] query_gateway_status called: order_id={order_id}")

        try:
            params = {"order_id": order_id}
            response = await self._call_tool_json("query_gateway_status", params)
            self._logger.debug(f"[PaymentMcpClient] query_gateway_status raw response: {response}")
            data = self._extract_success_data(response, tool="query_gateway_status")
            if not isinstance(data, dict):
                raise RuntimeError("MCP tool 'query_gateway_status' returned non-dict data payload")
            self._logger.info(f"[PaymentMcpClient] query_gateway_status success")
            return data
        except Exception as e:
            self._logger.exception(f"[PaymentMcpClient] query_gateway_status failed")
            raise


_client: PaymentMcpClient | None = None


def get_payment_mcp_client() -> PaymentMcpClient:
    from src.my_agent.payment_agent import a2a_payment_logger
    global _client
    if _client is None:
        _client = PaymentMcpClient(logger=a2a_payment_logger)
    return _client


async def create_order(
    context_id: str,
    items: list[dict[str, Any]],
    channel: str,
    customer_name: str = "",
    customer_email: str = "",
    customer_phone: str = "",
    customer_shipping_address: str = "",
    note: str = "",
    user_id: Optional[int] = None,
    conversation_id: Optional[str] = None
) -> dict[str, Any]:
    """Create an order using the shared MCP payment tool."""
    client = get_payment_mcp_client()
    return await client.create_order(
        context_id=context_id,
        items=items,
        channel=channel,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        customer_shipping_address=customer_shipping_address,
        note=note,
        user_id=user_id,
        conversation_id=conversation_id
    )


async def query_order_status(
    context_id: str,
    order_id: Optional[int] = None
) -> dict[str, Any]:
    """Query order status using the shared MCP payment tool."""
    client = get_payment_mcp_client()
    return await client.query_order_status(
        context_id=context_id,
        order_id=order_id
    )


async def query_gateway_status(order_id: int) -> dict[str, Any]:
    """Query payment gateway for actual order status."""
    client = get_payment_mcp_client()
    return await client.query_gateway_status(order_id=order_id)


create_order_tool = FunctionTool(create_order)
query_order_status_tool = FunctionTool(query_order_status)
query_gateway_status_tool = FunctionTool(query_gateway_status)