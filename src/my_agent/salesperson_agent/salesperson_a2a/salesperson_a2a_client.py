from __future__ import annotations

from typing import Any, Dict, Literal, List, Optional

from a2a.types import Message, DataPart
from google.adk.tools import FunctionTool

from src.config import PAYMENT_AGENT_SERVER_HOST, PAYMENT_AGENT_SERVER_PORT
from src.my_agent.my_a2a_common.payment_schemas import PaymentResponse
from src.my_agent.my_a2a_common.payment_schemas.payment_enums import PaymentChannel

from src.my_agent.base_a2a_client import BaseA2AClient
from src.my_agent.salesperson_agent.salesperson_a2a.prepare_payment_tasks import (
    prepare_create_order_payload,
    prepare_query_status_payload,
)
from src.utils.response_format_jsonrpc import ResponseFormatJSONRPC

PAYMENT_AGENT_BASE_URL = f"http://{PAYMENT_AGENT_SERVER_HOST}:{PAYMENT_AGENT_SERVER_PORT}"


class SalespersonA2AClient(BaseA2AClient):
    """Client used by the salesperson agent to reach the payment service."""

    def __init__(self, *, base_url: str | None = None, **kwargs: Any) -> None:
        from src.my_agent.salesperson_agent import salesperson_agent_logger as logger
        super().__init__(
            base_url=base_url or PAYMENT_AGENT_BASE_URL,
            endpoint_path="/",
            logger=logger,
            **kwargs,
        )
        self.logger.info("SalespersonA2AClient initialised (base_url=%s)", base_url or PAYMENT_AGENT_BASE_URL)

    async def create_order(
        self,
        items: List[Dict],
        customer: Dict[str, str],
        channel: PaymentChannel,
        user_id: int,
        *,
        note: str | None = None,
        metadata: Dict[str, str] | None = None,
    ) -> ResponseFormatJSONRPC:
        """Create an order by preparing the payload and forwarding it to A2A."""
        try:
            self.logger.debug(
                "create_order start (items=%d, channel=%s, user_id=%s, note=%s, has_metadata=%s)",
                len(items), channel.value, user_id, bool(note), bool(metadata),
            )
            payload = await prepare_create_order_payload(
                items,
                customer,
                channel,
                user_id,
                note=note,
                metadata=metadata,
            )
            message = await self.send_task(payload)
            response = _extract_payment_response(message)
            self.logger.info(
                "create_order ok (context_id=%s, status=%s, channel=%s, items=%d)",
                response.context_id, response.status.value, channel.value, len(items),
            )

            return ResponseFormatJSONRPC(
                data={
                    "message": message.model_dump(mode="json"),
                    "response": response.model_dump(mode="json"),
                }
            )
        except Exception:
            self.logger.exception("create_order failed")
            raise

    async def query_status(
        self,
        context_id: str,
        order_id: Optional[int] = None
    ) -> ResponseFormatJSONRPC:
        """Query the payment agent for the status of a previously created order.

        Args:
            context_id: Correlation ID of the original payment request
            order_id: Optional specific order ID to query (if not provided, returns all orders for context_id)
        """
        try:
            self.logger.info("query_status start (context_id=%s, order_id=%s)", context_id, order_id)
            payload = await prepare_query_status_payload(context_id, order_id=order_id)
            message = await self.send_task(payload)
            response = _extract_payment_response(message)
            self.logger.info(
                "query_status ok (context_id=%s, order_id=%s, status=%s)",
                response.context_id, order_id, response.status.value,
            )

            return ResponseFormatJSONRPC(
                data={
                    "message": message.model_dump(mode="json"),
                    "response": response.model_dump(mode="json"),
                }
            )
        except Exception:
            self.logger.exception("query_status failed (context_id=%s, order_id=%s)", context_id, order_id)
            raise


async def _create_payment_order(
    items: List[dict],
    customer: Dict[str, str],
    channel: Literal["redirect", "qr"],
    *,
    note: str,
    metadata: Dict[str, str],
) -> Dict[str, Any]:
    """Create a payment order for the customer.

    Args:
        items: List of items with name/sku and quantity
        customer: Customer information
        channel: Payment channel (redirect or qr)
        note: Order note
        metadata: Additional metadata

    Note:
        user_id is automatically retrieved from the execution context.
    """
    from src.my_agent.salesperson_agent.context import get_current_user_id

    user_id = get_current_user_id()

    async with SalespersonA2AClient() as client:
        client.logger.debug("tool _create_payment_order invoked (items=%d, channel=%s, user_id=%s)", len(items), channel, user_id)
        response = await client.create_order(
            items=items,
            customer=customer,
            channel=PaymentChannel(channel),
            user_id=user_id,
            note=note,
            metadata=metadata,
        )
    return response.to_dict()


async def query_payment_order_status(
    context_id: str,
    order_id: Optional[int] = None
) -> dict[str, Any]:
    """Query payment order status.

    Args:
        context_id: Correlation ID of the original payment request
        order_id: Optional specific order ID to query (if not provided, returns all orders for context_id)
    """
    async with SalespersonA2AClient() as client:
        client.logger.debug(
            "tool _query_payment_order_status invoked (context_id=%s, order_id=%s)",
            context_id, order_id
        )
        response = await client.query_status(context_id, order_id=order_id)
    return response.to_dict()


def _extract_payment_response(message: Message) -> PaymentResponse:
    """Convert the structured data ``Part`` back into a ``PaymentResponse``."""
    payload = None
    for part in message.parts:
        if isinstance(part.root, DataPart):
            payload = part.root.data
            break
    return PaymentResponse.model_validate(payload)


create_payment_order_tool = FunctionTool(_create_payment_order)
query_payment_order_status_tool = FunctionTool(query_payment_order_status)