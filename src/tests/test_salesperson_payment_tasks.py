from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from my_a2a_common import extract_payment_request
from my_a2a_common.payment_schemas.payment_enums import PaymentChannel

from my_agent.salesperson_agent.salesperson_a2a.payment_tasks import (
    build_salesperson_create_order_task,
    build_salesperson_query_status_task, prepare_create_order_payload, prepare_query_status_payload,
)
from my_agent.salesperson_agent.salesperson_mcp_client import SalespersonMcpClient


def _dummy_items() -> list[dict[str, object]]:
    return [
        {
            "sku": "ABC",
            "name": "Sample Product",
            "quantity": 1,
            "unit_price": 42.0,
            "currency": "USD",
        }
    ]


def _dummy_customer() -> dict[str, str]:
    return {"name": "Bob", "email": "bob@example.com"}


@pytest.mark.asyncio
async def test_build_salesperson_create_order_task_generates_system_fields() -> None:
    fake_client = AsyncMock(spec=SalespersonMcpClient)
    fake_client.generate_correlation_id.return_value = "CID-123"
    fake_client.generate_return_url.return_value = "https://return.example/CID-123"
    fake_client.generate_cancel_url.return_value = "https://cancel.example/CID-123"

    with patch(
        "my_agent.salesperson_agent.salesperson_a2a.payment_tasks.get_salesperson_mcp_client",
        return_value=fake_client,
    ):
        task = await build_salesperson_create_order_task(
            _dummy_items(),
            _dummy_customer(),
            PaymentChannel.REDIRECT,
        )

    fake_client.generate_correlation_id.assert_awaited_once_with(prefix="payment")
    fake_client.generate_return_url.assert_awaited_once_with("CID-123")
    fake_client.generate_cancel_url.assert_awaited_once_with("CID-123")

    request = extract_payment_request(task)
    assert request.correlation_id == "CID-123"
    assert request.method.return_url == "https://return.example/CID-123"
    assert request.method.cancel_url == "https://cancel.example/CID-123"


@pytest.mark.asyncio
async def test_build_salesperson_query_status_task_passthrough() -> None:
    task = await build_salesperson_query_status_task("CID-999")
    assert task.context_id == "CID-999"


@pytest.mark.asyncio
async def test_prepare_create_order_payload_wraps_task_and_request() -> None:
    fake_client = AsyncMock(spec=SalespersonMcpClient)
    fake_client.generate_correlation_id.return_value = "CID-777"
    fake_client.generate_return_url.return_value = "https://return.example/CID-777"
    fake_client.generate_cancel_url.return_value = "https://cancel.example/CID-777"

    result = await prepare_create_order_payload(
        _dummy_items(),
        _dummy_customer(),
        PaymentChannel.QR,
        mcp_client=fake_client,
    )

    assert result["correlation_id"] == "CID-777"
    assert result["payment_request"]["correlation_id"] == "CID-777"
    assert result["payment_request"]["method"]["channel"] == PaymentChannel.QR.value
    assert result["task"]["contextId"] == "CID-777"


@pytest.mark.asyncio
async def test_prepare_query_status_payload_wraps_task() -> None:
    result = await prepare_query_status_payload("CID-4242")

    assert result["correlation_id"] == "CID-4242"
    assert result["status_request"]["correlation_id"] == "CID-4242"
    assert result["task"]["contextId"] == "CID-4242"
