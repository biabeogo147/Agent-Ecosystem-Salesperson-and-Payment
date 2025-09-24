"""Async helper for calling salesperson MCP tools over HTTP.

This module centralises the code that connects to the salesperson MCP server
so that other modules (such as :mod:`payment_tasks`) no longer import the
in-process tool implementations directly. Keeping the networking logic here
makes it easy to swap the transport in the future and gives us a clean seam
for unit tests.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from google.adk.tools.mcp_tool.mcp_session_manager import (
    MCPSessionManager,
    StreamableHTTPConnectionParams,
)
from mcp import types as mcp_types

from config import MCP_SERVER_HOST_SALESPERSON, MCP_SERVER_PORT_SALESPERSON

_DEFAULT_STREAMABLE_HTTP_URL = (
    f"http://{MCP_SERVER_HOST_SALESPERSON}:{MCP_SERVER_PORT_SALESPERSON}/mcp"
)


class SalespersonMcpClient:
    """Small wrapper around :class:`MCPSessionManager` for salesperson tools."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        session_manager: MCPSessionManager | None = None,
    ) -> None:
        self._base_url = base_url or _DEFAULT_STREAMABLE_HTTP_URL
        self._session_manager = session_manager or MCPSessionManager(
            StreamableHTTPConnectionParams(url=self._base_url)
        )

    async def _call_tool(
        self, name: str, arguments: Optional[dict[str, Any]] = None
    ) -> mcp_types.CallToolResult:
        session = await self._session_manager.create_session()
        result = await session.call_tool(name, arguments)
        if result.isError:
            raise RuntimeError(
                f"MCP tool '{name}' returned an error payload: {result}"
            )
        return result

    async def _call_tool_text(
        self, name: str, arguments: Optional[dict[str, Any]] = None
    ) -> str:
        result = await self._call_tool(name, arguments)
        for part in result.content:
            if isinstance(part, mcp_types.TextContent):
                return part.text
        if result.structuredContent is not None:
            return json.dumps(result.structuredContent)
        raise RuntimeError(
            f"MCP tool '{name}' returned no textual content to interpret."
        )

    async def _call_tool_json(
        self, name: str, arguments: Optional[dict[str, Any]] = None
    ) -> Any:
        """Call a tool and interpret its response as JSON-compatible data."""

        result = await self._call_tool(name, arguments)
        if result.structuredContent is not None:
            return result.structuredContent

        for part in result.content:
            if isinstance(part, mcp_types.TextContent):
                if not part.text.strip():
                    continue
                try:
                    return json.loads(part.text)
                except json.JSONDecodeError as exc:
                    snippet = part.text[:200]
                    raise RuntimeError(
                        f"MCP tool '{name}' returned non-JSON text: {snippet}"
                    ) from exc

        raise RuntimeError(
            f"MCP tool '{name}' returned no JSON content to interpret."
        )

    async def generate_correlation_id(self, *, prefix: str) -> str:
        """Request a new correlation ID from the MCP server."""

        return await self._call_tool_text(
            "generate_correlation_id", {"prefix": prefix}
        )

    async def generate_return_url(self, correlation_id: str) -> str:
        """Request the return URL bound to ``correlation_id`` from MCP."""

        return await self._call_tool_text(
            "generate_return_url", {"correlation_id": correlation_id}
        )

    async def generate_cancel_url(self, correlation_id: str) -> str:
        """Request the cancel URL bound to ``correlation_id`` from MCP."""

        return await self._call_tool_text(
            "generate_cancel_url", {"correlation_id": correlation_id}
        )

    async def find_product(self, *, query: str) -> dict[str, Any]:
        """Look up products via the MCP ``find_product`` tool."""

        payload = await self._call_tool_json("find_product", {"query": query})
        if not isinstance(payload, dict):
            raise RuntimeError(
                "MCP tool 'find_product' returned an unexpected payload type"
            )
        return payload

    async def calc_shipping(self, *, weight: float, distance: float) -> dict[str, Any]:
        """Calculate shipping costs using the shared MCP shipping tool."""

        payload = await self._call_tool_json(
            "calc_shipping", {"weight": weight, "distance": distance}
        )
        if not isinstance(payload, dict):
            raise RuntimeError(
                "MCP tool 'calc_shipping' returned an unexpected payload type"
            )
        return payload

    async def reserve_stock(self, *, sku: str, quantity: int) -> dict[str, Any]:
        """Reserve inventory using the MCP stock management tool."""

        payload = await self._call_tool_json(
            "reserve_stock", {"sku": sku, "quantity": quantity}
        )
        if not isinstance(payload, dict):
            raise RuntimeError(
                "MCP tool 'reserve_stock' returned an unexpected payload type"
            )
        return payload


_client: SalespersonMcpClient | None = None


def get_salesperson_mcp_client() -> SalespersonMcpClient:
    """Return a process-wide :class:`SalespersonMcpClient` singleton."""

    global _client
    if _client is None:
        _client = SalespersonMcpClient()
    return _client


__all__ = ["SalespersonMcpClient", "get_salesperson_mcp_client"]
