import pytest
from httpx import ASGITransport, AsyncClient

from a2a.types import (
    Message,
    MessageSendParams,
    Role,
    SendMessageRequest,
    SendMessageResponse,
    Task,
    TaskState,
    TaskStatus,
)
from my_agent.payment_agent.payment_a2a import a2a_app as payment_app_module
from my_agent.payment_agent.payment_a2a.payment_agent_skills import (
    CREATE_ORDER_SKILL_ID,
    QUERY_STATUS_SKILL_ID,
)
from my_a2a_common.payment_schemas import (
    CustomerInfo,
    PaymentItem,
    PaymentMethod,
    PaymentRequest,
    QueryStatusRequest,
)
from my_a2a_common.payment_schemas.payment_enums import (
    PaymentAction,
    PaymentChannel,
    PaymentStatus,
)


@pytest.mark.asyncio
async def test_payment_app_routes_create_order(monkeypatch: pytest.MonkeyPatch) -> None:
    app = payment_app_module.a2a_app
    payment_request = PaymentRequest(
        protocol="my_a2a_common.v1",
        correlation_id="corr-create",
        from_agent="sales",
        to_agent="payment",
        action=PaymentAction.CREATE_ORDER,
        items=[
            PaymentItem(
                sku="SKU-1",
                name="Item",
                quantity=1,
                unit_price=10.0,
                currency="USD",
            )
        ],
        customer=CustomerInfo(
            name="Alice",
            email="alice@example.com",
            phone="123456789",
        ),
        method=PaymentMethod(
            channel=PaymentChannel("redirect"),
            return_url="https://return",
            cancel_url="https://cancel",
        ),
    )

    captured: dict[str, dict] = {}

    async def fake_create_order(payload: dict) -> dict:
        captured["payload"] = payload
        return {
            "correlation_id": payment_request.correlation_id,
            "status": PaymentStatus.SUCCESS.value,
            "order_id": "ORD-123",
            "provider_name": "TestPay",
        }

    async def fail_query(_: dict) -> dict:
        raise AssertionError("query_order_status should not be called")

    monkeypatch.setattr(payment_app_module.payment_handler, "_create_order_tool", fake_create_order)
    monkeypatch.setattr(payment_app_module.payment_handler, "_query_status_tool", fail_query)
    monkeypatch.setattr(
        "my_agent.salesperson_agent.salesperson_a2a.payment_tasks.extract_payment_request",
        lambda task: payment_request,
    )

    message = Message(
        context_id=payment_request.correlation_id,
        message_id="msg-create",
        role=Role.user,
        parts=[],
    )
    task = Task(
        id="task-create",
        context_id=payment_request.correlation_id,
        history=[message],
        status=TaskStatus(state=TaskState.submitted),
        metadata={
            "skill_id": CREATE_ORDER_SKILL_ID,
            "correlation_id": payment_request.correlation_id,
        },
    )

    params = MessageSendParams(
        message=message,
        metadata={"task": task.model_dump(mode="json")},
    )
    request = SendMessageRequest(id="req-create", params=params)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/", json=request.model_dump(mode="json"))

    assert response.status_code == 200
    rpc_response = SendMessageResponse.model_validate(response.json())
    assert isinstance(rpc_response.root.result, Message)
    assert rpc_response.root.result.kind == "message"
    assert captured["payload"]["correlation_id"] == payment_request.correlation_id


@pytest.mark.asyncio
async def test_payment_app_routes_query_status(monkeypatch: pytest.MonkeyPatch) -> None:
    app = payment_app_module.a2a_app
    status_request = QueryStatusRequest(correlation_id="corr-status")

    captured: dict[str, dict] = {}

    async def fake_query(payload: dict) -> dict:
        captured["payload"] = payload
        return {
            "correlation_id": status_request.correlation_id,
            "status": PaymentStatus.PENDING.value,
            "provider_name": "TestPay",
        }

    async def fail_create(_: dict) -> dict:
        raise AssertionError("create_order should not be called")

    monkeypatch.setattr(payment_app_module.payment_handler, "_query_status_tool", fake_query)
    monkeypatch.setattr(payment_app_module.payment_handler, "_create_order_tool", fail_create)
    monkeypatch.setattr(
        "my_agent.salesperson_agent.salesperson_a2a.payment_tasks.extract_status_request",
        lambda task: status_request,
    )

    message = Message(
        context_id=status_request.correlation_id,
        message_id="msg-status",
        role=Role.user,
        parts=[],
    )
    task = Task(
        id="task-status",
        context_id=status_request.correlation_id,
        history=[message],
        status=TaskStatus(state=TaskState.submitted),
        metadata={
            "skill_id": QUERY_STATUS_SKILL_ID,
            "correlation_id": status_request.correlation_id,
        },
    )

    params = MessageSendParams(
        message=message,
        metadata={"task": task.model_dump(mode="json")},
    )
    request = SendMessageRequest(id="req-status", params=params)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/", json=request.model_dump(mode="json"))

    assert response.status_code == 200
    rpc_response = SendMessageResponse.model_validate(response.json())
    assert isinstance(rpc_response.root.result, Message)
    assert rpc_response.root.result.kind == "message"
    assert captured["payload"]["correlation_id"] == status_request.correlation_id
