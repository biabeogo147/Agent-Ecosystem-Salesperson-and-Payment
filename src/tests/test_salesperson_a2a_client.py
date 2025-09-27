from __future__ import annotations

import json

import httpx
import pytest

from a2a.types import Task, TaskState, TaskStatus

from my_a2a_common import build_create_order_message, build_payment_response_message
from my_a2a_common.payment_schemas import (
    CustomerInfo,
    PaymentItem,
    PaymentMethod,
    PaymentRequest,
    PaymentResponse,
)
from my_a2a_common.payment_schemas.payment_enums import PaymentChannel, PaymentStatus
from my_agent.salesperson_agent.salesperson_a2a import salesperson_a2a_client
from my_agent.salesperson_agent.salesperson_a2a.salesperson_a2a_client import SalespersonA2AClient


def _build_order_task() -> Task:
    payment_request = PaymentRequest(
        correlation_id="corr-123",
        items=[
            PaymentItem(
                sku="sku-1",
                name="Widget",
                quantity=1,
                unit_price=25.0,
                currency="USD",
            )
        ],
        customer=CustomerInfo(name="Alice", email="alice@example.com"),
        method=PaymentMethod(
            channel=PaymentChannel.REDIRECT,
            return_url="https://return",
            cancel_url="https://cancel",
        ),
    )

    message = build_create_order_message(payment_request)
    return Task(
        id="task-123",
        context_id=payment_request.correlation_id,
        history=[message],
        status=TaskStatus(state=TaskState.submitted),
        metadata={
            "skill_id": "payment.create-order",
            "correlation_id": payment_request.correlation_id,
        },
    )


@pytest.mark.asyncio
async def test_salesperson_a2a_client_parses_payment_response(monkeypatch: pytest.MonkeyPatch) -> None:
    task = _build_order_task()

    async def fake_prepare_create_order_payload(*args, **kwargs):
        return {"task": task.model_dump(mode="json")}

    monkeypatch.setattr(
        salesperson_a2a_client,
        "prepare_create_order_payload",
        fake_prepare_create_order_payload,
    )

    response = PaymentResponse(
        correlation_id="corr-123",
        status=PaymentStatus.SUCCESS,
        order_id="order-999",
    )
    response_message = build_payment_response_message(response)

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        assert body["params"]["metadata"]["task"]["contextId"] == "corr-123"
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": body["id"],
                "result": {
                    "status": "00",
                    "message": "SUCCESS",
                    "data": response_message.model_dump(mode="json"),
                },
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://payment.example") as http_client:
        async with SalespersonA2AClient(base_url="https://payment.example", client=http_client) as client:
            result = await client.create_order(
                items=[{"sku": "sku-1", "quantity": 1}],
                customer={"name": "Alice", "email": "alice@example.com"},
                channel="redirect",
            )

    assert result.data["response"]["correlation_id"] == "corr-123"
    assert result.data["response"]["order_id"] == "order-999"
    assert result.data["response"]["status"] == PaymentStatus.SUCCESS.value


@pytest.mark.asyncio
async def test_salesperson_a2a_client_queries_status(monkeypatch: pytest.MonkeyPatch) -> None:
    task = _build_order_task()

    async def fake_prepare_query_status_payload(correlation_id: str):
        assert correlation_id == "corr-123"
        return {"task": task.model_dump(mode="json")}

    monkeypatch.setattr(
        salesperson_a2a_client,
        "prepare_query_status_payload",
        fake_prepare_query_status_payload,
    )

    response = PaymentResponse(
        correlation_id="corr-123",
        status=PaymentStatus.PENDING,
        order_id="order-999",
    )
    response_message = build_payment_response_message(response)

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        assert body["params"]["metadata"]["task"]["contextId"] == "corr-123"
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": body["id"],
                "result": {
                    "status": "00",
                    "message": "SUCCESS",
                    "data": response_message.model_dump(mode="json"),
                },
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://payment.example") as http_client:
        async with SalespersonA2AClient(base_url="https://payment.example", client=http_client) as client:
            result = await client.query_status("corr-123")

    assert result.data["response"]["status"] == PaymentStatus.PENDING.value
