from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from my_a2a_common.payment_schemas.payment_enums import PaymentChannel

from my_agent.salesperson_agent.salesperson_a2a.payment_tasks import (
    build_salesperson_create_order_task,
    build_salesperson_query_status_task,
    prepare_query_status_payload,
    prepare_create_order_payload_with_client,
    extract_payment_request,
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


def _minimal_items() -> list[dict[str, object]]:
    return [
        {
            "name": "Sample Product",
            "quantity": 1,
        }
    ]


def _dummy_customer() -> dict[str, str]:
    return {"name": "Bob", "email": "bob@example.com"}


def _fake_client(correlation_id: str) -> SalespersonMcpClient:
    fake_client = AsyncMock(spec=SalespersonMcpClient)

    async def _generate_correlation_id(*, prefix: str) -> str:
        assert prefix == "payment"
        return correlation_id

    async def _generate_return_url(value: str) -> str:
        assert value == correlation_id
        return f"https://return.example/{value}"

    async def _generate_cancel_url(value: str) -> str:
        assert value == correlation_id
        return f"https://cancel.example/{value}"

    async def _find_product(*, query: str) -> dict[str, object]:
        assert query == "Sample Product"
        return {
            "status": "00",
            "message": "SUCCESS",
            "data": [
                {
                    "sku": "ABC",
                    "name": "Sample Product",
                    "price": 42.0,
                    "currency": "USD",
                }
            ],
        }

    fake_client.generate_correlation_id.side_effect = _generate_correlation_id
    fake_client.generate_return_url.side_effect = _generate_return_url
    fake_client.generate_cancel_url.side_effect = _generate_cancel_url
    fake_client.find_product.side_effect = _find_product
    return fake_client


@pytest.mark.asyncio
async def test_build_salesperson_create_order_task_generates_system_fields() -> None:
    fake_client = _fake_client("CID-123")

    task = await build_salesperson_create_order_task(
        _dummy_items(),
        _dummy_customer(),
        PaymentChannel.REDIRECT,
        mcp_client=fake_client,
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
    fake_client = _fake_client("CID-777")

    result = await prepare_create_order_payload_with_client(
        _minimal_items(),
        _dummy_customer(),
        "qr",
        client=fake_client,
    )

    assert result["correlation_id"] == "CID-777"
    assert result["payment_request"]["correlation_id"] == "CID-777"
    assert result["payment_request"]["method"]["channel"] == "qr"
    assert result["task"]["contextId"] == "CID-777"
    fake_client.find_product.assert_awaited_once_with(query="Sample Product")
    assert result["payment_request"]["items"][0]["unit_price"] == 42.0
    assert result["payment_request"]["items"][0]["sku"] == "ABC"


@pytest.mark.asyncio
async def test_prepare_query_status_payload_wraps_task() -> None:
    result = await prepare_query_status_payload("CID-4242")

    assert result["correlation_id"] == "CID-4242"
    assert result["status_request"]["correlation_id"] == "CID-4242"
    assert result["task"]["contextId"] == "CID-4242"
