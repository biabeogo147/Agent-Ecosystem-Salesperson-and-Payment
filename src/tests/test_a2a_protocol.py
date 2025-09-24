from __future__ import annotations

import pytest
from a2a.types import Role, TaskState

from my_a2a import (
    CREATE_ORDER_SKILL_ID,
    PaymentAgentHandler,
    QUERY_STATUS_SKILL_ID,
    build_create_order_task,
    build_payment_agent_card,
    build_query_status_task,
    extract_payment_request,
    extract_payment_response,
    extract_status_request,
)
from my_a2a.payment_schemas.payment_enums import NextActionType, PaymentChannel


def _correlation_id(prefix: str) -> str:
    assert prefix == "payment"
    return "CID-001"


def _url_factory(correlation_id: str) -> tuple[str, str]:
    return f"https://return/{correlation_id}", f"https://cancel/{correlation_id}"


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
    cid = _correlation_id("payment")
    return_url, cancel_url = _url_factory(cid)
    task = await build_create_order_task(
        _dummy_items(),
        _dummy_customer(),
        PaymentChannel.REDIRECT,
        cid, return_url, cancel_url,
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
    task = await build_query_status_task("CID-001")
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

    cid = _correlation_id("payment")
    return_url, cancel_url = _url_factory(cid)
    task = await build_create_order_task(
        _dummy_items(),
        _dummy_customer(),
        PaymentChannel.REDIRECT,
        cid, return_url, cancel_url,
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
        query_status_tool=lambda payload: payload,  # unused
    )

    cid = _correlation_id("payment")
    return_url, cancel_url = _url_factory(cid)
    task = await build_create_order_task(
        _dummy_items(),
        _dummy_customer(),
        PaymentChannel.REDIRECT,
        cid, return_url, cancel_url,
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
