from __future__ import annotations
import json
from unittest.mock import AsyncMock, patch

import pytest

from src.my_agent.payment_agent.payment_mcp_client import (
    PaymentMcpClient,
    create_order as create_order_wrapper,
    query_order_status as query_order_status_wrapper,
)
from src.my_agent.my_a2a_common.payment_schemas.payment_enums import (
    NextActionType,
    PaymentChannel,
    PaymentStatus,
)
from src.config import CHECKOUT_URL, PAYGATE_PROVIDER, QR_URL
from src.utils.status import Status


@pytest.mark.asyncio
async def test_create_order_redirect_channel() -> None:
    from src.my_mcp.payment.tools_for_payment_agent import create_order

    payload = {
        "context_id": "corr-123",
        "items": [
            {
                "sku": "SKU001",
                "name": "Widget",
                "quantity": 2,
                "unit_price": 15.0,
                "currency": "USD",
            }
        ],
        "customer": {"name": "Alice"},
        "method": {
            "channel": PaymentChannel.REDIRECT.value,
            "return_url": "https://example.com/return",
            "cancel_url": "https://example.com/cancel",
        },
    }

    response_json = await create_order(payload)
    envelope = json.loads(response_json)
    assert envelope["status"] == Status.SUCCESS.value
    assert envelope["message"] == "SUCCESS"

    response = envelope["data"]
    assert response["status"] == PaymentStatus.PENDING.value
    assert response["provider_name"] == PAYGATE_PROVIDER
    assert response["next_action"]["type"] == NextActionType.REDIRECT.value
    assert response["pay_url"].startswith(f"{CHECKOUT_URL}/")
    assert response["next_action"]["url"] == response["pay_url"]
    assert response["qr_code_url"] is None
    assert response["next_action"]["qr_code_url"] is None
    assert response["context_id"] == "corr-123"
    assert response["order_id"]
    assert response["expires_at"] == response["next_action"]["expires_at"]


@pytest.mark.asyncio
async def test_create_order_qr_channel() -> None:
    from src.my_mcp.payment.tools_for_payment_agent import create_order

    payload = {
        "context_id": "corr-qr",
        "items": [
            {
                "sku": "SKU002",
                "name": "Gadget",
                "quantity": 1,
                "unit_price": 42.0,
                "currency": "USD",
            }
        ],
        "customer": {"name": "Bob"},
        "method": {
            "channel": PaymentChannel.QR.value,
            "return_url": None,
            "cancel_url": None,
        },
    }

    response_json = await create_order(payload)
    envelope = json.loads(response_json)
    assert envelope["status"] == Status.SUCCESS.value
    assert envelope["message"] == "SUCCESS"

    response = envelope["data"]
    assert response["status"] == PaymentStatus.PENDING.value
    assert response["next_action"]["type"] == NextActionType.SHOW_QR.value
    assert response["pay_url"] is None
    assert response["next_action"]["url"] is None
    assert response["qr_code_url"].startswith(f"{QR_URL}/")
    assert response["next_action"]["qr_code_url"] == response["qr_code_url"]


@pytest.mark.asyncio
async def test_query_order_status_returns_failed() -> None:
    from src.my_mcp.payment.tools_for_payment_agent import query_order_status

    response_json = await query_order_status({"context_id": "corr-xyz"})
    envelope = json.loads(response_json)
    assert envelope["status"] == Status.SUCCESS.value
    response = envelope["data"]

    assert response["context_id"] == "corr-xyz"
    assert response["status"] == PaymentStatus.FAILED.value


@pytest.mark.asyncio
async def test_payment_client_create_order_delegates_to_json_call() -> None:
    client = PaymentMcpClient(base_url="http://example.com")
    client._call_tool_json = AsyncMock(
        return_value={
            "status": Status.SUCCESS.value,
            "message": "SUCCESS",
            "data": {"status": "SUCCESS"},
        }
    )

    payload = {"foo": "bar"}
    result = await client.create_order(payload=payload)

    client._call_tool_json.assert_awaited_once_with("create_order", {"payload": payload})
    assert result == {"status": "SUCCESS"}


@pytest.mark.asyncio
async def test_payment_client_create_order_rejects_non_dict_payload() -> None:
    client = PaymentMcpClient(base_url="http://example.com")
    client._call_tool_json = AsyncMock(return_value=["unexpected"])

    with pytest.raises(RuntimeError):
        await client.create_order(payload={})


@pytest.mark.asyncio
async def test_payment_client_query_order_status_delegates_to_json_call() -> None:
    client = PaymentMcpClient(base_url="http://example.com")
    client._call_tool_json = AsyncMock(
        return_value={
            "status": Status.SUCCESS.value,
            "message": "SUCCESS",
            "data": {"status": "PENDING"},
        }
    )

    payload = {"context_id": "corr-123"}
    result = await client.query_order_status(payload=payload)

    client._call_tool_json.assert_awaited_once_with("query_order_status", {"payload": payload})
    assert result == {"status": "PENDING"}


@pytest.mark.asyncio
async def test_payment_client_query_order_status_rejects_non_dict_payload() -> None:
    client = PaymentMcpClient(base_url="http://example.com")
    client._call_tool_json = AsyncMock(return_value="unexpected")

    with pytest.raises(RuntimeError):
        await client.query_order_status(payload={"context_id": "foo"})


@pytest.mark.asyncio
async def test_create_order_wrapper_uses_singleton_client() -> None:
    fake_client = AsyncMock(spec=PaymentMcpClient)
    fake_client.create_order.return_value = {"status": "SUCCESS"}

    with patch(
        "src.my_agent.payment_agent.payment_mcp_client.get_payment_mcp_client",
        return_value=fake_client,
    ):
        result = await create_order_wrapper({"foo": "bar"})

    fake_client.create_order.assert_awaited_once_with(payload={"foo": "bar"})
    assert result == {"status": "SUCCESS"}


@pytest.mark.asyncio
async def test_query_order_status_wrapper_uses_singleton_client() -> None:
    fake_client = AsyncMock(spec=PaymentMcpClient)
    fake_client.query_order_status.return_value = {"status": "FAILED"}

    with patch(
        "src.my_agent.payment_agent.payment_mcp_client.get_payment_mcp_client",
        return_value=fake_client,
    ):
        result = await query_order_status_wrapper({"context_id": "abc"})

    fake_client.query_order_status.assert_awaited_once_with(payload={"context_id": "abc"})
    assert result == {"status": "FAILED"}