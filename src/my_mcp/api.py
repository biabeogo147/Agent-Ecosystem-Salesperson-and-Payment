"""Core logic for the MCP tool microservice."""

from __future__ import annotations

import inspect
import json
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Mapping

from utils.app_string import (
    INVALID_TOOL_ARGUMENT,
    SUCCESS,
    TOOL_EXECUTION_ERROR,
    TOOL_INVOCATION_COMPLETED,
    TOOL_NOT_FOUND,
    UNKNOWN_ENDPOINT,
)
from utils.response_format import ResponseFormat
from utils.status import Status
from utils.urls import MCP_URLS

from .tools import calc_shipping, find_product, reserve_stock

logger = logging.getLogger(__name__)

ToolCallable = Callable[..., Awaitable[Any] | Any]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    handler: ToolCallable
    input_schema: Mapping[str, Any]


def _build_registry() -> dict[str, ToolDefinition]:
    return {
        "find_product": ToolDefinition(
            name="find_product",
            description="Find a product by SKU or fuzzy name search.",
            handler=find_product,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SKU or partial product name to search for.",
                    }
                },
                "required": ["query"],
            },
        ),
        "calc_shipping": ToolDefinition(
            name="calc_shipping",
            description="Calculate shipping cost based on weight and distance.",
            handler=calc_shipping,
            input_schema={
                "type": "object",
                "properties": {
                    "weight": {
                        "type": "number",
                        "description": "Package weight in kilograms.",
                    },
                    "distance": {
                        "type": "number",
                        "description": "Shipping distance in kilometres.",
                    },
                },
                "required": ["weight", "distance"],
            },
        ),
        "reserve_stock": ToolDefinition(
            name="reserve_stock",
            description="Reserve a quantity of stock for a provided SKU.",
            handler=reserve_stock,
            input_schema={
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Product SKU that should be reserved.",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of units to reserve.",
                    },
                },
                "required": ["sku", "quantity"],
            },
        ),
    }


class MCPService:
    """Encapsulates the business logic of the MCP tool service."""

    def __init__(self, registry: Mapping[str, ToolDefinition] | None = None):
        self._registry = dict(registry or _build_registry())

    async def list_tools(self) -> tuple[int, Any]:
        tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._registry.values()
        ]
        body = ResponseFormat(status=Status.SUCCESS, message=SUCCESS, data=tools)
        return 200, body.to_dict()

    async def invoke_tool(self, tool_name: str, arguments: Mapping[str, Any]) -> tuple[int, Any]:
        tool = self._registry.get(tool_name)
        if tool is None:
            body = ResponseFormat(
                status=Status.TOOL_NOT_FOUND,
                message=f"{TOOL_NOT_FOUND}: {tool_name}",
                data={"tool": tool_name},
            )
            return 404, body.to_dict()

        try:
            result = tool.handler(**arguments)
            if inspect.isawaitable(result):
                result = await result
        except TypeError as exc:
            logger.exception("Invalid arguments for tool '%s': %s", tool_name, exc)
            body = ResponseFormat(
                status=Status.INVALID_TOOL_ARGUMENT,
                message=f"{INVALID_TOOL_ARGUMENT}: {exc}",
                data={"tool": tool_name, "arguments": dict(arguments)},
            )
            return 422, body.to_dict()
        except Exception as exc:  # pragma: no cover - defensive safeguard
            logger.exception("Tool '%s' failed during execution", tool_name)
            body = ResponseFormat(
                status=Status.TOOL_EXECUTION_ERROR,
                message=f"{TOOL_EXECUTION_ERROR}: {exc}",
                data={"tool": tool_name},
            )
            return 500, body.to_dict()

        parsed = _safe_parse_json(result)
        if isinstance(parsed, Mapping) and {"status", "message", "data"}.issubset(parsed):
            try:
                tool_status = Status(parsed.get("status", Status.SUCCESS.value))
            except ValueError:
                tool_status = Status.SUCCESS
            response = ResponseFormat(
                status=tool_status,
                message=parsed.get("message", SUCCESS),
                data={
                    "tool": tool_name,
                    "result": parsed,
                    "raw": result if not isinstance(result, (dict, list)) else None,
                },
            )
        else:
            response = ResponseFormat(
                status=Status.SUCCESS,
                message=TOOL_INVOCATION_COMPLETED,
                data={
                    "tool": tool_name,
                    "result": parsed if parsed is not None else result,
                    "raw": result if parsed is not None else None,
                },
            )
        payload = response.to_dict()
        data = payload.get("data")
        if isinstance(data, dict) and data.get("raw") is None:
            data.pop("raw", None)
        return 200, payload

    async def dispatch(self, method: str, path: str, payload: Any | None) -> tuple[int, Any]:
        """Helper used by HTTP adapters to route requests."""

        if method == "GET" and path == MCP_URLS.list_tools:
            return await self.list_tools()
        invoke_prefix = MCP_URLS.tool_invoke_prefix
        invoke_suffix = MCP_URLS.tool_invoke_suffix
        if method == "POST" and path.startswith(invoke_prefix) and path.endswith(invoke_suffix):
            tool_name = path[len(invoke_prefix) : -len(invoke_suffix)]
            arguments = payload.get("arguments", {}) if isinstance(payload, Mapping) else {}
            return await self.invoke_tool(tool_name, arguments)
        if method == "GET" and path == MCP_URLS.health:
            body = ResponseFormat(
                status=Status.SUCCESS,
                message=SUCCESS,
                data={"service": "mcp"},
            )
            return 200, body.to_dict()
        body = ResponseFormat(
            status=Status.UNKNOWN_ENDPOINT,
            message=UNKNOWN_ENDPOINT,
            data={"path": path},
        )
        return 404, body.to_dict()


def _safe_parse_json(data: Any) -> Any | None:
    if isinstance(data, (dict, list)):
        return data
    if isinstance(data, (bytes, bytearray)):
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError:
            return None
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None
    return None


def create_app() -> MCPService:
    """Factory maintained for backwards compatibility with earlier API."""

    return MCPService()


__all__ = ["MCPService", "create_app"]
