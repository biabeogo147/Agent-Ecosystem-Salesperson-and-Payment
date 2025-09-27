"""Starlette application that exposes the payment agent over JSON-RPC."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from a2a.types import AgentCapabilities, AgentCard, MessageSendParams, Task
from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from config import PAYMENT_AGENT_SERVER_HOST, PAYMENT_AGENT_SERVER_PORT
from my_a2a_common.a2a_salesperson_payment.constants import JSON_MEDIA_TYPE
from .payment_agent_skills import CREATE_ORDER_SKILL, QUERY_STATUS_SKILL
from utils.response_format import ResponseFormat

from my_agent.payment_agent.payment_a2a.payment_agent_handler import PaymentAgentHandler
from my_agent.payment_agent.payment_mcp_client import create_order, query_order_status


logger = logging.getLogger(__name__)


def build_payment_agent_card(base_url: str) -> AgentCard:
    """Describe the payment agent using the official SDK models."""

    capabilities = AgentCapabilities(
        streaming=False,
        push_notifications=False,
        state_transition_history=False,
    )

    return AgentCard(
        name="Payment Agent",
        description="Processes checkout requests coming from the salesperson agent.",
        version="1.0.0",
        url=base_url,
        default_input_modes=[JSON_MEDIA_TYPE],
        default_output_modes=[JSON_MEDIA_TYPE],
        capabilities=capabilities,
        skills=[CREATE_ORDER_SKILL, QUERY_STATUS_SKILL],
    )


def _sync_adapter(async_callable):
    async def _run(payload: dict[str, Any]) -> dict[str, Any]:
        return await async_callable(payload)

    def _wrapper(payload: dict[str, Any]) -> dict[str, Any]:
        return asyncio.run(_run(payload))

    return _wrapper


_PAYMENT_HANDLER = PaymentAgentHandler(
    create_order_tool=_sync_adapter(create_order),
    query_status_tool=_sync_adapter(query_order_status),
)

_CARD_BASE_URL = f"http://{PAYMENT_AGENT_SERVER_HOST}:{PAYMENT_AGENT_SERVER_PORT}/"
_PAYMENT_AGENT_CARD = build_payment_agent_card(_CARD_BASE_URL)


def _json_rpc_error_response(
    request_id: str | None,
    *,
    code: int,
    message: str,
    data: Any | None = None,
) -> JSONResponse:
    error_payload: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error_payload["data"] = data

    status_code = 500 if code == -32603 else 400 if code == -32700 else 200
    return JSONResponse(
        {"jsonrpc": "2.0", "id": request_id, "error": error_payload},
        status_code=status_code,
    )


async def _handle_message_send(request: Request) -> Response:
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        return _json_rpc_error_response(None, code=-32700, message="Invalid JSON payload")

    request_id = payload.get("id")
    if payload.get("jsonrpc") != "2.0":
        return _json_rpc_error_response(request_id, code=-32600, message="Invalid JSON-RPC version")

    if payload.get("method") != "message.send":
        return _json_rpc_error_response(request_id, code=-32601, message="Unsupported method")

    params_payload = payload.get("params")
    if params_payload is None:
        return _json_rpc_error_response(request_id, code=-32602, message="Missing params")

    try:
        params = MessageSendParams.model_validate(params_payload)
    except ValidationError as exc:
        return _json_rpc_error_response(request_id, code=-32602, message="Invalid params", data=exc.errors())

    metadata = params.metadata or {}
    task_payload = metadata.get("task")
    if task_payload is None:
        return _json_rpc_error_response(request_id, code=-32602, message="Missing task metadata")

    try:
        task = Task.model_validate(task_payload)
    except ValidationError as exc:
        return _json_rpc_error_response(request_id, code=-32602, message="Invalid task payload", data=exc.errors())

    try:
        message = await asyncio.to_thread(_PAYMENT_HANDLER.handle_task, task)
    except Exception as exc:  # pragma: no cover - defensive path
        logger.exception("Payment agent failed to handle task")
        return _json_rpc_error_response(request_id, code=-32603, message="Internal error", data=str(exc))

    response_format = ResponseFormat(data=message.model_dump(mode="json"))
    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": response_format.to_dict(),
        }
    )


async def _handle_agent_card(_: Request) -> Response:
    return JSONResponse(_PAYMENT_AGENT_CARD.model_dump(mode="json"))


routes = [
    Route("/.well-known/agent.json", _handle_agent_card, methods=["GET"]),
    Route("/", _handle_message_send, methods=["POST"]),
]


a2a_app = Starlette(debug=False, routes=routes)


__all__ = ["a2a_app", "build_payment_agent_card"]
