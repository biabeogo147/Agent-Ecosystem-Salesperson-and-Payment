"""FastAPI controller exposing MCP tools over HTTP and WebSocket."""

from __future__ import annotations

import json
import logging
from typing import Any, Mapping

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from utils.app_string import INVALID_JSON_BODY, INVALID_REQUEST_PAYLOAD
from utils.response_format import ResponseFormat
from utils.status import Status
from utils.urls import MCP_URLS

from .service import MCPService

logger = logging.getLogger(__name__)


async def _send_ws_response(websocket: WebSocket, status_code: int, body: Mapping[str, Any]) -> None:
    """Send a response envelope back to the WebSocket client."""

    await websocket.send_json({"status_code": status_code, "body": dict(body)})


def create_fastapi_app(service: MCPService | None = None) -> FastAPI:
    """Create a FastAPI application exposing MCP tooling capabilities."""

    mcp_service = service or MCPService()
    app = FastAPI(title="MCP Tool Service", version="1.0.0")

    @app.get(MCP_URLS.health)
    async def healthcheck() -> JSONResponse:  # pragma: no cover - thin wrapper
        status_code, body = await mcp_service.dispatch("GET", MCP_URLS.health, None)
        return JSONResponse(status_code=status_code, content=body)

    @app.get(MCP_URLS.list_tools)
    async def list_tools() -> JSONResponse:
        status_code, body = await mcp_service.list_tools()
        return JSONResponse(status_code=status_code, content=body)

    @app.post(MCP_URLS.tool_invoke)
    async def invoke_tool(tool_name: str, request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            response = ResponseFormat(
                status=Status.INVALID_JSON,
                message=INVALID_JSON_BODY,
                data=None,
            ).to_dict()
            return JSONResponse(status_code=400, content=response)

        if payload is None:
            payload = {}
        if not isinstance(payload, Mapping):
            response = ResponseFormat(
                status=Status.INVALID_REQUEST,
                message=f"{INVALID_REQUEST_PAYLOAD}: payload must be an object.",
                data={"issue": "invalid_payload"},
            ).to_dict()
            return JSONResponse(status_code=400, content=response)

        arguments = payload.get("arguments") or {}
        if not isinstance(arguments, Mapping):
            response = ResponseFormat(
                status=Status.INVALID_REQUEST,
                message=f"{INVALID_REQUEST_PAYLOAD}: arguments must be an object.",
                data={"issue": "invalid_arguments"},
            ).to_dict()
            return JSONResponse(status_code=400, content=response)

        status_code, body = await mcp_service.invoke_tool(tool_name, dict(arguments))
        return JSONResponse(status_code=status_code, content=body)

    @app.websocket(MCP_URLS.websocket)
    async def websocket_handler(websocket: WebSocket) -> None:
        await websocket.accept()
        while True:
            try:
                message = await websocket.receive_text()
            except WebSocketDisconnect:  # pragma: no cover - network event
                break
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.exception("WebSocket receive failure: %s", exc)
                break

            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                response = ResponseFormat(
                    status=Status.INVALID_JSON,
                    message=INVALID_JSON_BODY,
                    data=None,
                ).to_dict()
                await _send_ws_response(websocket, 400, response)
                continue

            if not isinstance(payload, Mapping):
                response = ResponseFormat(
                    status=Status.INVALID_REQUEST,
                    message=f"{INVALID_REQUEST_PAYLOAD}: payload must be an object.",
                    data={"issue": "invalid_payload"},
                ).to_dict()
                await _send_ws_response(websocket, 400, response)
                continue

            action = payload.get("action")
            if action == "list_tools":
                status_code, body = await mcp_service.list_tools()
                await _send_ws_response(websocket, status_code, body)
                continue

            if action == "invoke_tool":
                tool_name = payload.get("name") or payload.get("tool")
                if not isinstance(tool_name, str) or not tool_name:
                    response = ResponseFormat(
                        status=Status.INVALID_REQUEST,
                        message=f"{INVALID_REQUEST_PAYLOAD}: missing tool name.",
                        data={"issue": "missing_tool"},
                    ).to_dict()
                    await _send_ws_response(websocket, 400, response)
                    continue
                arguments = payload.get("arguments") or {}
                if not isinstance(arguments, Mapping):
                    response = ResponseFormat(
                        status=Status.INVALID_REQUEST,
                        message=f"{INVALID_REQUEST_PAYLOAD}: arguments must be an object.",
                        data={"issue": "invalid_arguments"},
                    ).to_dict()
                    await _send_ws_response(websocket, 400, response)
                    continue
                status_code, body = await mcp_service.invoke_tool(tool_name, dict(arguments))
                await _send_ws_response(websocket, status_code, body)
                continue

            response = ResponseFormat(
                status=Status.INVALID_REQUEST,
                message=f"{INVALID_REQUEST_PAYLOAD}: unsupported action '{action}'.",
                data={"action": action},
            ).to_dict()
            await _send_ws_response(websocket, 400, response)

    return app


app = create_fastapi_app()


__all__ = ["app", "create_fastapi_app"]
