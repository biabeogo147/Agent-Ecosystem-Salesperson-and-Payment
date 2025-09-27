import json
from unittest.mock import AsyncMock

import pytest

from a2a.types import SendMessageRequest
from my_agent.base_a2a_client import BaseA2AClient
from my_agent.salesperson_agent.salesperson_a2a.client import SalespersonA2AClient
from utils.status import Status


def test_base_a2a_extract_success_returns_data() -> None:
    payload = {"status": Status.SUCCESS.value, "message": "ok", "data": {"foo": "bar"}}
    result = BaseA2AClient._extract_success_data(payload, operation="demo")
    assert result == {"foo": "bar"}


def test_base_a2a_extract_success_raises_on_error_status() -> None:
    payload = {"status": Status.FAILURE.value, "message": "boom", "data": {}}
    with pytest.raises(RuntimeError):
        BaseA2AClient._extract_success_data(payload, operation="demo")


@pytest.mark.asyncio
async def test_salesperson_a2a_create_order_posts_task(monkeypatch: pytest.MonkeyPatch) -> None:
    client = SalespersonA2AClient(base_url="https://payment.example")
    mock_post = AsyncMock(
        return_value={
            "status": Status.SUCCESS.value,
            "message": "",
            "data": {"order_id": "ORD-1"},
        }
    )
    monkeypatch.setattr(client, "_post_json", mock_post)

    payload = {
        "task": {
            "id": "task-1",
            "context_id": "ctx-1",
            "status": {"state": "submitted"},
            "history": [
                {"kind": "message", "role": "user", "message_id": "mid-1", "parts": [], "context_id": "ctx-1"}
            ],
        }
    }
    result = await client.create_order(payload)

    assert result == {"order_id": "ORD-1"}
    mock_post.assert_awaited_once()
    assert mock_post.await_args[0][0] == "/"
    request_payload = SendMessageRequest.model_validate(mock_post.await_args[0][1])
    assert request_payload.params.metadata is not None
    assert request_payload.params.metadata["task"]["id"] == "task-1"


@pytest.mark.asyncio
async def test_salesperson_a2a_query_status_accepts_json_strings(monkeypatch: pytest.MonkeyPatch) -> None:
    client = SalespersonA2AClient(base_url="https://payment.example")
    mock_post = AsyncMock(
        return_value={
            "status": Status.SUCCESS.value,
            "message": "",
            "data": {"status": "pending"},
        }
    )
    monkeypatch.setattr(client, "_post_json", mock_post)

    raw_payload = json.dumps(
        {
            "task": json.dumps(
                {
                    "id": "task-42",
                    "context_id": "ctx-42",
                    "status": {"state": "submitted"},
                    "history": [
                        {
                            "kind": "message",
                            "role": "user",
                            "message_id": "mid-42",
                            "parts": [],
                            "context_id": "ctx-42",
                        }
                    ],
                }
            )
        }
    )
    result = await client.query_status(raw_payload)

    assert result == {"status": "pending"}
    submitted_payload = SendMessageRequest.model_validate(mock_post.await_args[0][1])
    assert submitted_payload.params.metadata is not None
    assert submitted_payload.params.metadata["task"]["id"] == "task-42"


def test_salesperson_a2a_requires_task_entry() -> None:
    client = SalespersonA2AClient(base_url="https://payment.example")
    with pytest.raises(ValueError):
        client._normalise_task_envelope({}, operation="unit-test")

