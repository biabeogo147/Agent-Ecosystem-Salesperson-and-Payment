from __future__ import annotations

from unittest.mock import patch, AsyncMock

import pytest

from my_a2a import extract_payment_request
from my_a2a.payment_schemas.payment_enums import PaymentChannel

from my_agent.salesperson_agent.payment_tasks import (
    build_salesperson_create_order_task,
    build_salesperson_query_status_task,
)


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
    with (
        patch(
            "my_mcp.salesperson.tools_for_salesperson_agent.generate_correlation_id",
            new_callable=AsyncMock,
        ) as mock_corr,
        patch(
            "my_mcp.salesperson.tools_for_salesperson_agent.generate_return_url",
            new_callable=AsyncMock,
        ) as mock_return,
        patch(
            "my_mcp.salesperson.tools_for_salesperson_agent.generate_cancel_url",
            new_callable=AsyncMock,
        ) as mock_cancel,
    ):
        mock_corr.return_value = "CID-123"
        mock_return.return_value = "https://return.example/CID-123"
        mock_cancel.return_value = "https://cancel.example/CID-123"
        task = await build_salesperson_create_order_task(
            _dummy_items(),
            _dummy_customer(),
            PaymentChannel.REDIRECT,
        )

    mock_corr.assert_awaited_once_with(prefix="payment")
    mock_return.assert_awaited_once_with("CID-123")
    mock_cancel.assert_awaited_once_with("CID-123")

    request = extract_payment_request(task)
    assert request.correlation_id == "CID-123"
    assert request.method.return_url == "https://return.example/CID-123"
    assert request.method.cancel_url == "https://cancel.example/CID-123"


@pytest.mark.asyncio
async def test_build_salesperson_query_status_task_passthrough() -> None:
    task = await build_salesperson_query_status_task("CID-999")
    assert task.context_id == "CID-999"
