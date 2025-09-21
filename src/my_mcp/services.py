"""Service layer for MCP FastAPI endpoints."""

from __future__ import annotations

import asyncio
import inspect
import json
import uuid
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from my_mcp import tools as mcp_tools


@dataclass
class ToolDefinition:
    """Holds metadata and callable reference for a single tool."""

    name: str
    description: str
    parameters: List[Dict[str, Any]]
    func: Callable[..., Awaitable[Any] | Any]


def _build_tool_definition(func: Callable[..., Any]) -> ToolDefinition:
    """Create a ToolDefinition from a callable."""

    signature = inspect.signature(func)
    parameters: List[Dict[str, Any]] = []

    for name, param in signature.parameters.items():
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue

        annotation: Optional[str] = None
        if param.annotation is not inspect._empty:
            annotation = getattr(param.annotation, "__name__", str(param.annotation))

        default: Any = None
        required = True
        if param.default is not inspect._empty:
            default = param.default
            required = False

        parameters.append(
            {
                "name": name,
                "type": annotation,
                "required": required,
                "default": default,
            }
        )

    return ToolDefinition(
        name=func.__name__,
        description=inspect.getdoc(func) or "",
        parameters=parameters,
        func=func,
    )


TOOL_DEFINITIONS: Dict[str, ToolDefinition] = {
    definition.name: definition
    for definition in (
        _build_tool_definition(mcp_tools.find_product),
        _build_tool_definition(mcp_tools.calc_shipping),
        _build_tool_definition(mcp_tools.reserve_stock),
    )
}


class ToolInvokeRequest(BaseModel):
    client_id: str = Field(..., description="Unique identifier of the caller's SSE session")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments passed to the tool")


class ToolInvokeResponse(BaseModel):
    status: str
    event_id: str


class ToolListResponse(BaseModel):
    tools: List[Dict[str, Any]]


class EventBroker:
    """Manages SSE queues per connected client."""

    def __init__(self) -> None:
        self._clients: Dict[str, asyncio.Queue[Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, client_id: str) -> asyncio.Queue[Dict[str, Any]]:
        async with self._lock:
            queue = self._clients.get(client_id)
            if queue is None:
                queue = asyncio.Queue()
                self._clients[client_id] = queue
            return queue

    async def disconnect(self, client_id: str) -> None:
        async with self._lock:
            self._clients.pop(client_id, None)

    async def publish(self, client_id: str, message: Dict[str, Any]) -> None:
        queue = await self.connect(client_id)
        await queue.put(message)


broker = EventBroker()


async def _execute_tool(definition: ToolDefinition, arguments: Dict[str, Any]) -> Any:
    func = definition.func
    if inspect.iscoroutinefunction(func):
        return await func(**arguments)
    return await asyncio.to_thread(func, **arguments)


async def _stream_events(client_id: str) -> AsyncGenerator[str, None]:
    queue = await broker.connect(client_id)
    try:
        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield f"data: {json.dumps(payload)}\n\n"
            except asyncio.TimeoutError:
                # Keep the connection alive while no events are available.
                yield ": keep-alive\n\n"
    except asyncio.CancelledError:
        raise
    finally:
        await broker.disconnect(client_id)


async def list_tools() -> ToolListResponse:
    """Expose metadata about the available tools."""

    return ToolListResponse(
        tools=[
            {
                "name": definition.name,
                "description": definition.description,
                "parameters": definition.parameters,
            }
            for definition in TOOL_DEFINITIONS.values()
        ]
    )


async def stream(client_id: str) -> StreamingResponse:
    """Establish an SSE stream for the given client identifier."""

    if not client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="client_id is required")

    generator = _stream_events(client_id)
    return StreamingResponse(generator, media_type="text/event-stream")


async def invoke_tool(tool_name: str, request: ToolInvokeRequest) -> ToolInvokeResponse:
    """Schedule tool execution and stream the result back to the caller."""

    definition = TOOL_DEFINITIONS.get(tool_name)
    if definition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tool '{tool_name}' not found")

    event_id = str(uuid.uuid4())

    async def _run_tool() -> None:
        try:
            result = await _execute_tool(definition, request.arguments)
            payload = {
                "event_id": event_id,
                "tool": tool_name,
                "status": "success",
                "result": result,
            }
        except Exception as exc:  # noqa: BLE001 - surface tool errors to caller
            payload = {
                "event_id": event_id,
                "tool": tool_name,
                "status": "error",
                "error": str(exc),
            }
        await broker.publish(request.client_id, payload)

    asyncio.create_task(_run_tool())

    return ToolInvokeResponse(status="scheduled", event_id=event_id)
