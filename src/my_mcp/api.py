"""Core logic for the MCP tool microservice."""

from __future__ import annotations

import inspect
import json
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Mapping

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
        return 200, tools

    async def invoke_tool(self, tool_name: str, arguments: Mapping[str, Any]) -> tuple[int, Any]:
        tool = self._registry.get(tool_name)
        if tool is None:
            return 404, {
                "status": "error",
                "message": f"Tool '{tool_name}' is not registered.",
            }

        try:
            result = tool.handler(**arguments)
            if inspect.isawaitable(result):
                result = await result
        except TypeError as exc:
            logger.exception("Invalid arguments for tool '%s': %s", tool_name, exc)
            return 422, {
                "status": "error",
                "message": f"Invalid arguments for tool '{tool_name}': {exc}",
            }
        except Exception as exc:  # pragma: no cover - defensive safeguard
            logger.exception("Tool '%s' failed during execution", tool_name)
            return 500, {
                "status": "error",
                "message": f"Tool '{tool_name}' failed to execute: {exc}",
            }

        parsed = _safe_parse_json(result)
        body = {
            "status": "success",
            "tool": tool_name,
            "result": parsed if parsed is not None else result,
        }
        if parsed is not None:
            body["raw"] = result
        return 200, body

    async def dispatch(self, method: str, path: str, payload: Any | None) -> tuple[int, Any]:
        """Helper used by HTTP adapters to route requests."""

        if method == "GET" and path == "/v1/tools":
            return await self.list_tools()
        if method == "POST" and path.startswith("/v1/tools/") and path.endswith(":invoke"):
            tool_name = path[len("/v1/tools/") : -len(":invoke")]
            arguments = payload.get("arguments", {}) if isinstance(payload, Mapping) else {}
            return await self.invoke_tool(tool_name, arguments)
        if method == "GET" and path == "/healthz":
            return 200, {"status": "ok"}
        return 404, {"status": "error", "message": "Unknown endpoint."}


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
