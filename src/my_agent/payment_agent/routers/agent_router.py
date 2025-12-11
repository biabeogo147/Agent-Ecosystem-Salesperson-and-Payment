from __future__ import annotations

import json

from a2a.types import Task, MessageSendParams
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError

from src.config import PAYMENT_AGENT_SERVER_HOST, PAYMENT_AGENT_SERVER_PORT
from src.my_agent.payment_agent import a2a_payment_logger as logger
from src.my_agent.payment_agent.services import payment_service
from my_agent.payment_agent.utils.a2a_util import build_payment_agent_card
from src.utils.response_format_jsonrpc import ResponseFormatJSONRPC
from src.utils.status import Status


agent_router = APIRouter(tags=["A2A"])

# Build agent card at module level
_CARD_BASE_URL = f"http://{PAYMENT_AGENT_SERVER_HOST}:{PAYMENT_AGENT_SERVER_PORT}/"
_AGENT_CARD = build_payment_agent_card(_CARD_BASE_URL)


@agent_router.get("/.well-known/agent-card.json")
async def get_agent_card():
    """Return the A2A agent card for this agent."""
    logger.debug("agent-card requested")
    return JSONResponse(content=_AGENT_CARD.model_dump(mode="json"))


@agent_router.post("/")
async def message_send(request: Request) -> Response:
    """
    Handle A2A message.send JSON-RPC requests.

    This endpoint receives JSON-RPC 2.0 requests with method "message.send"
    and dispatches them to the appropriate skill handler via payment_service.
    """
    # Parse JSON body
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        logger.warning("message.send: invalid JSON body")
        return ResponseFormatJSONRPC(
            status=Status.JSON_INVALID,
            message="Invalid JSON payload"
        ).to_response()

    request_id = payload.get("id")
    logger.info("message.send received (id=%s)", request_id)
    logger.debug("Payload: %s", payload)

    # Validate JSON-RPC version
    if payload.get("jsonrpc") != "2.0":
        logger.warning("message.send: invalid JSON-RPC version: %s", payload.get("jsonrpc"))
        return ResponseFormatJSONRPC(
            id=request_id,
            status=Status.JSON_RPC_VERSION_INVALID,
            message="Invalid JSON-RPC version"
        ).to_response()

    # Validate method
    if payload.get("method") != "message.send":
        logger.warning("message.send: unsupported method: %s", payload.get("method"))
        return ResponseFormatJSONRPC(
            id=request_id,
            status=Status.METHOD_NOT_FOUND,
            message="Unsupported method"
        ).to_response()

    # Extract and validate params
    params_payload = payload.get("params")
    if params_payload is None:
        logger.warning("message.send: missing params")
        return ResponseFormatJSONRPC(
            id=request_id,
            status=Status.MISSING_PARAMS,
            message="Missing params"
        ).to_response()

    try:
        params = MessageSendParams.model_validate(params_payload)
    except ValidationError as exc:
        logger.warning("message.send: invalid params (errors=%d)", len(exc.errors()))
        return ResponseFormatJSONRPC(
            id=request_id,
            status=Status.INVALID_PARAMS,
            message="Invalid params",
            data=exc.errors()
        ).to_response()

    # Extract task from metadata
    metadata = params.metadata or {}
    task_payload = metadata.get("task")
    if task_payload is None:
        logger.warning("message.send: missing task metadata")
        return ResponseFormatJSONRPC(
            id=request_id,
            status=Status.MISSING_TASK_METADATA,
            message="Missing task metadata"
        ).to_response()

    hinted_skill = (task_payload.get("metadata") or {}).get("skill_id")
    if hinted_skill:
        logger.debug("message.send: hinted skill_id=%s", hinted_skill)

    # Validate task payload
    try:
        task = Task.model_validate(task_payload)
    except ValidationError as exc:
        logger.warning("message.send: invalid task payload (errors=%d)", len(exc.errors()))
        return ResponseFormatJSONRPC(
            id=request_id,
            status=Status.INVALID_TASK_PAYLOAD,
            message="Invalid task payload",
            data=exc.errors(),
        ).to_response()

    # Dispatch to payment service for business logic
    try:
        message = await payment_service.handle_task(task)
    except Exception as exc:
        logger.exception("Error while handling task")
        return ResponseFormatJSONRPC(
            id=request_id,
            status=Status.UNKNOWN_ERROR,
            message="Internal error",
            data=str(exc),
        ).to_response()

    logger.info("message.send handled successfully (id=%s)", request_id)
    return ResponseFormatJSONRPC(data=message.model_dump(mode="json")).to_response()
