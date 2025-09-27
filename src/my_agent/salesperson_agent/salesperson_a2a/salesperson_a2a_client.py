"""Convenience wrapper for the salesperson agent to call the payment agent."""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, Literal, List

from google.adk.tools import FunctionTool

from config import PAYMENT_AGENT_SERVER_HOST, PAYMENT_AGENT_SERVER_PORT
from my_a2a_common import extract_payment_response
from my_a2a_common.payment_schemas.payment_enums import PaymentChannel

from my_agent.base_a2a_client import BaseA2AClient
from my_agent.salesperson_agent.salesperson_a2a.prepare_payment_tasks import (
    prepare_create_order_payload,
    prepare_query_status_payload,
)
from utils.response_format_jsonrpc import ResponseFormatJSONRPC


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LOG_DIR = os.path.join(PROJECT_ROOT, "log")
os.makedirs(LOG_DIR, exist_ok=True)

log_file_path = os.path.join(LOG_DIR, "salesperson_a2a_client.log")

logger = logging.getLogger(__name__)
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(file_handler)

PAYMENT_AGENT_BASE_URL = f"http://{PAYMENT_AGENT_SERVER_HOST}:{PAYMENT_AGENT_SERVER_PORT}"


class SalespersonA2AClient(BaseA2AClient):
    """Client used by the salesperson agent to reach the payment service."""

    def __init__(self, *, base_url: str | None = None, **kwargs: Any) -> None:
        super().__init__(
            base_url=base_url or PAYMENT_AGENT_BASE_URL,
            endpoint_path="/",
            logger=logger,
            **kwargs,
        )
        self._logger.info("SalespersonA2AClient initialised (base_url=%s)", base_url or PAYMENT_AGENT_BASE_URL)

    async def create_order(
        self,
        items: List[Any],
        customer: Dict[str, str],
        channel: PaymentChannel,
        *,
        note: str | None = None,
        metadata: Dict[str, str] | None = None,
    ) -> ResponseFormatJSONRPC:
        """Create an order by preparing the payload and forwarding it to A2A."""
        try:
            self._logger.debug(
                "create_order start (items=%d, channel=%s, note=%s, has_metadata=%s)",
                len(items), channel.value, bool(note), bool(metadata),
            )
            payload = await prepare_create_order_payload(
                items,
                customer,
                channel,
                note=note,
                metadata=metadata,
            )
            message = await self.send_task_payload(payload)
            response = extract_payment_response(message)
            self._logger.info(
                "create_order ok (correlation_id=%s, status=%s, channel=%s, items=%d)",
                response.correlation_id, response.status.value, channel.value, len(items),
            )

            return ResponseFormatJSONRPC(
                data={
                    "message": message.model_dump(mode="json"),
                    "response": response.model_dump(mode="json"),
                }
            )
        except Exception:
            self._logger.exception("create_order failed")
            raise

    async def query_status(self, correlation_id: str) -> ResponseFormatJSONRPC:
        """Query the payment agent for the status of a previously created order."""
        try:
            self._logger.info("query_status start (correlation_id=%s)", correlation_id)
            payload = await prepare_query_status_payload(correlation_id)
            message = await self.send_task_payload(payload)
            response = extract_payment_response(message)
            self._logger.info(
                "query_status ok (correlation_id=%s, status=%s)",
                response.correlation_id, response.status.value,
            )

            return ResponseFormatJSONRPC(
                data={
                    "message": message.model_dump(mode="json"),
                    "response": response.model_dump(mode="json"),
                }
            )
        except Exception:
            self._logger.exception("query_status failed (correlation_id=%s)", correlation_id)
            raise


async def _create_payment_order(
    items: List[Any],
    customer: Dict[str, str],
    channel: Literal["redirect", "qr"],
    *,
    note: str,
    metadata: Dict[str, str],
) -> Dict[str, Any]:
    logger.debug("tool _create_payment_order invoked (items=%d, channel=%s)", len(items), channel)
    async with SalespersonA2AClient() as client:
        response = await client.create_order(
            items=items,
            customer=customer,
            channel=PaymentChannel(channel),
            note=note,
            metadata=metadata,
        )
    return response.to_dict()


async def _query_payment_order_status(correlation_id: str) -> dict[str, Any]:
    logger.debug("tool _query_payment_order_status invoked (correlation_id=%s)", correlation_id)
    async with SalespersonA2AClient() as client:
        response = await client.query_status(correlation_id)
    return response.to_dict()


create_payment_order_tool = FunctionTool(_create_payment_order)
query_payment_order_status_tool = FunctionTool(_query_payment_order_status)

__all__ = [
    "SalespersonA2AClient",
    "PAYMENT_AGENT_BASE_URL",
    "create_payment_order_tool",
    "query_payment_order_status_tool",
]
