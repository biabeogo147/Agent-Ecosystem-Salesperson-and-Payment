from __future__ import annotations

import json

import httpx
import pytest

from a2a.types import Message, Role, Task, TaskState, TaskStatus

from my_agent.base_a2a_client import BaseA2AClient
from utils.status import Status


def _build_task() -> Task:
    message = Message(message_id="msg-1", role=Role.user, context_id="ctx-1", parts=[])
    return Task(
        id="task-1",
        context_id="ctx-1",
        history=[message],
        status=TaskStatus(state=TaskState.submitted),
        metadata={"skill_id": "test.skill", "correlation_id": "ctx-1"},
    )


@pytest.mark.asyncio
async def test_base_a2a_client_send_task_success() -> None:
    task = _build_task()
    response_message = Message(message_id="resp-1", role=Role.agent, context_id="ctx-1", parts=[])

    captured_request: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["url"] = str(request.url)
        body = json.loads(request.content.decode())
        captured_request["body"] = body
        assert body["method"] == "message.send"
        metadata = body["params"]["metadata"]
        assert metadata["task"]["metadata"]["skill_id"] == "test.skill"
        assert metadata["task"]["history"][0]["messageId"] == "msg-1"
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": body["id"],
                "result": {
                    "status": Status.SUCCESS.value,
                    "message": "SUCCESS",
                    "data": response_message.model_dump(mode="json"),
                },
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://payment.example") as http_client:
        async with BaseA2AClient(base_url="https://payment.example", client=http_client) as client:
            message = await client.send_task(task)

    assert captured_request["url"].endswith("/")
    assert message.message_id == "resp-1"
    assert message.role is Role.agent


@pytest.mark.asyncio
async def test_base_a2a_client_raises_on_error_status() -> None:
    task = _build_task()

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": body["id"],
                "result": {
                    "status": Status.FAILURE.value,
                    "message": "gateway failure",
                    "data": {},
                },
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://payment.example") as http_client:
        async with BaseA2AClient(base_url="https://payment.example", client=http_client) as client:
            with pytest.raises(RuntimeError, match="status '01'"):
                await client.send_task(task)
