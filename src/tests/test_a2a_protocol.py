from __future__ import annotations

from collections.abc import Callable
from unittest.mock import AsyncMock

import pytest
from a2a.types import Role, TaskState

from my_a2a_common import (
    CREATE_ORDER_SKILL_ID,
    PaymentAgentHandler,
    QUERY_STATUS_SKILL_ID,
    extract_payment_response,
)
from my_a2a_common.payment_schemas.payment_enums import NextActionType, PaymentChannel

from my_agent.payment_agent.payment_a2a.a2a_app import build_payment_agent_card
from my_agent.salesperson_agent.salesperson_mcp_client import SalespersonMcpClient
from my_agent.salesperson_agent.salesperson_a2a.payment_tasks import build_salesperson_create_order_task, \
    build_salesperson_query_status_task, extract_payment_request, extract_status_request


def _fake_client(
    correlation_id: str,
) -> SalespersonMcpClient:
    fake_client = AsyncMock(spec=SalespersonMcpClient)

    async def _generate_correlation_id(*, prefix: str) -> str:
        assert prefix == "payment"
        return correlation_id

    async def _generate_return_url(value: str) -> str:
        assert value == correlation_id
        return f"https://return/{value}"

    async def _generate_cancel_url(value: str) -> str:
        assert value == correlation_id
        return f"https://cancel/{value}"

    fake_client.generate_correlation_id.side_effect = _generate_correlation_id
    fake_client.generate_return_url.side_effect = _generate_return_url
    fake_client.generate_cancel_url.side_effect = _generate_cancel_url
    return fake_client


def _dummy_items() -> list[dict]:
    return [
        {
            "sku": "SKU-1",
            "name": "Product 1",
            "quantity": 1,
            "unit_price": 10.0,
            "currency": "USD",
        }
    ]


def _dummy_customer() -> dict:
    return {"name": "Alice", "email": "alice@example.com"}


@pytest.mark.asyncio
async def test_build_create_order_task_injects_system_fields() -> None:
    fake_client = _fake_client("CID-001")
    task = await build_salesperson_create_order_task(
        _dummy_items(),
        _dummy_customer(),
        PaymentChannel.REDIRECT,
        mcp_client=fake_client,
    )

    request = extract_payment_request(task)

    assert request.correlation_id == "CID-001"
    assert request.method.return_url == "https://return/CID-001"
    assert request.method.cancel_url == "https://cancel/CID-001"
    assert request.method.channel == PaymentChannel.REDIRECT
    # The helper also fills in the surrounding A2A metadata for newcomers to inspect.
    assert task.context_id == "CID-001"
    assert task.metadata["skill_id"] == CREATE_ORDER_SKILL_ID
    assert task.status.state is TaskState.submitted
    assert task.history[0].role is Role.user


@pytest.mark.asyncio
async def test_build_query_status_task_wraps_payload() -> None:
    task = await build_salesperson_query_status_task("CID-001")
    status_request = extract_status_request(task)
    assert status_request.correlation_id == "CID-001"
    assert task.metadata["skill_id"] == QUERY_STATUS_SKILL_ID


@pytest.mark.asyncio
async def test_payment_agent_handler_validates_and_wraps_response() -> None:
    def create_order_tool(payload: dict) -> dict:
        assert payload["correlation_id"] == "CID-001"
        return {
            "correlation_id": payload["correlation_id"],
            "status": "PENDING",
            "next_action": {"type": "REDIRECT", "url": "https://pay.example.com"},
        }

    def query_status_tool(payload: dict) -> dict:
        return {
            "correlation_id": payload["correlation_id"],
            "status": "PENDING",
            "next_action": {"type": "NONE"},
        }

    handler = PaymentAgentHandler(
        create_order_tool=create_order_tool,
        query_status_tool=query_status_tool,
    )

    fake_client = _fake_client("CID-001")

    task = await build_salesperson_create_order_task(
        _dummy_items(),
        _dummy_customer(),
        PaymentChannel.REDIRECT,
        mcp_client=fake_client,
    )

    message = handler.handle_task(task)
    response = extract_payment_response(message)

    assert response.correlation_id == "CID-001"
    assert response.next_action.type == NextActionType.REDIRECT
    assert response.next_action.url == "https://pay.example.com"
    assert message.role is Role.agent
    assert message.context_id == "CID-001"


@pytest.mark.asyncio
async def test_payment_agent_handler_rejects_invalid_response() -> None:
    def create_order_tool(_payload: dict) -> dict:
        return {
            "correlation_id": "WRONG",
            "status": "PENDING",
            "next_action": {"type": "NONE"},
        }

    handler = PaymentAgentHandler(
        create_order_tool=create_order_tool,
        query_status_tool=lambda payload: payload,
    )

    fake_client = _fake_client("CID-001")

    task = await build_salesperson_create_order_task(
        _dummy_items(),
        _dummy_customer(),
        PaymentChannel.REDIRECT,
        mcp_client=fake_client,
    )

    with pytest.raises(ValueError):
        handler.handle_task(task)


def test_build_payment_agent_card_includes_payment_skills() -> None:
    card = build_payment_agent_card("https://payments.example/rpc/")

    assert str(card.url) == "https://payments.example/rpc/"
    skill_ids = {skill.id for skill in card.skills}
    assert skill_ids == {
        "payment.create-order",
        "payment.query-status",
    }
    assert card.default_input_modes == ["application/json"]
    assert card.default_output_modes == ["application/json"]
