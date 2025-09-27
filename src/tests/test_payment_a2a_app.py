from __future__ import annotations

import json

import httpx
import pytest

from a2a.types import MessageSendParams, Task, TaskState, TaskStatus

from my_a2a_common import build_create_order_message, build_payment_response_message
from my_a2a_common.payment_schemas import CustomerInfo, PaymentItem, PaymentMethod, PaymentRequest, PaymentResponse
from my_a2a_common.payment_schemas.payment_enums import PaymentChannel, PaymentStatus
from importlib import import_module

a2a_app_module = import_module("my_agent.payment_agent.payment_a2a.a2a_app")
from utils.status import Status


def _order_task() -> Task:
    request = PaymentRequest(
        correlation_id="corr-abc",
        items=[
            PaymentItem(
                sku="sku-10",
                name="Adapter",
                quantity=2,
                unit_price=15.0,
                currency="USD",
            )
        ],
        customer=CustomerInfo(name="Bob", email="bob@example.com"),
        method=PaymentMethod(
            channel=PaymentChannel.REDIRECT,
            return_url="https://return",
            cancel_url="https://cancel",
        ),
    )
    message = build_create_order_message(request)
    return Task(
        id="task-abc",
        context_id=request.correlation_id,
        history=[message],
        status=TaskStatus(state=TaskState.submitted),
        metadata={
            "skill_id": "payment.create-order",
            "correlation_id": request.correlation_id,
        },
    )


class _DummyHandler:
    def __init__(self, response_message):
        self._response_message = response_message
        self.calls = 0
        self.last_task: Task | None = None

    def handle_task(self, task: Task):
        self.calls += 1
        self.last_task = task
        return self._response_message


@pytest.mark.asyncio
async def test_payment_a2a_app_message_send(monkeypatch) -> None:
    task = _order_task()
    payload = {"task": task.model_dump(mode="json")}
    params = MessageSendParams(
        message=task.history[-1],
        metadata=payload,
    )

    payment_response = PaymentResponse(
        correlation_id="corr-abc",
        status=PaymentStatus.SUCCESS,
        order_id="order-abc",
    )
    response_message = build_payment_response_message(payment_response)

    dummy_handler = _DummyHandler(response_message)
    monkeypatch.setattr(a2a_app_module, "_PAYMENT_HANDLER", dummy_handler)

    transport = httpx.ASGITransport(app=a2a_app_module.a2a_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/",
            json={
                "jsonrpc": "2.0",
                "id": "req-1",
                "method": "message.send",
                "params": params.model_dump(mode="json"),
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["status"] == Status.SUCCESS.value
    assert body["result"]["data"]["contextId"] == "corr-abc"
    assert dummy_handler.calls == 1
    assert dummy_handler.last_task is not None
    assert dummy_handler.last_task.metadata["skill_id"] == "payment.create-order"


@pytest.mark.asyncio
async def test_payment_a2a_app_missing_task_metadata() -> None:
    params = MessageSendParams(message=_order_task().history[-1], metadata={})

    transport = httpx.ASGITransport(app=a2a_app_module.a2a_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/",
            json={
                "jsonrpc": "2.0",
                "id": "req-err",
                "method": "message.send",
                "params": params.model_dump(mode="json"),
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["error"]["code"] == -32602
    assert "task" in body["error"]["message"]
