from __future__ import annotations

import json
from typing import Any, Optional

from mcp import types as mcp_types
from google.adk.tools.mcp_tool.mcp_session_manager import MCPSessionManager

from src.my_mcp.mcp_connect_params import get_mcp_streamable_http_connect_params
from src.utils.status import Status


class BaseMcpClient:
    """Base helper that wraps :class:`MCPSessionManager` interactions."""

    def __init__(
        self,
        *,
        logger: logging.Logger,
        base_url: str,
        token: str,
        session_manager: MCPSessionManager | None = None,
    ) -> None:
        self._logger = logger
        self._base_url = base_url
        self._session_manager = session_manager or MCPSessionManager(
            get_mcp_streamable_http_connect_params(self._base_url, token)
        )

    async def _call_tool(
        self, name: str, arguments: Optional[dict[str, Any]] = None
    ) -> mcp_types.CallToolResult:
        self._logger.debug(f"[MCP] Calling tool '{name}' with arguments: {arguments}")
        try:
            session = await self._session_manager.create_session()
            self._logger.debug(f"[MCP] Session created for tool '{name}'")
            result = await session.call_tool(name, arguments)
            if result.isError:
                self._logger.error(f"[MCP] Tool '{name}' returned error payload: {result}")
                raise RuntimeError(f"MCP tool '{name}' returned an error payload: {result}")
            self._logger.debug(f"[MCP] Tool '{name}' returned successfully: {result}")
            return result
        except Exception as e:
            self._logger.exception(f"[MCP] Exception while calling tool '{name}'")
            raise

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

    @staticmethod
    def _ensure_response_format(payload: Any, *, tool: str) -> dict[str, Any]:
        """Validate that ``payload`` conforms to the ResponseFormat contract."""
        if not isinstance(payload, dict):
            raise RuntimeError(
                f"MCP tool '{tool}' returned an unexpected payload type: {type(payload)!r}"
            )

        missing_keys = [key for key in ("status", "message", "data") if key not in payload]
        if missing_keys:
            raise RuntimeError(
                f"MCP tool '{tool}' returned a malformed response missing keys: {missing_keys}"
            )

        return payload

    @classmethod
    def _extract_success_data(cls, payload: Any, *, tool: str) -> Any:
        """Return the ``data`` field when the ResponseFormat indicates success."""
        response = cls._ensure_response_format(payload, tool=tool)
        status = response.get("status")
        if status != Status.SUCCESS.value:
            message = response.get("message", "")
            raise RuntimeError(
                f"MCP tool '{tool}' returned status '{status}': {message}"
            )

        return response.get("data")