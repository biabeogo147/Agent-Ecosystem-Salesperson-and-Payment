from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MCPURLs:
    """URL mapping for the MCP tool microservice."""

    list_tools: str = "/v1/tools"
    tool_invoke: str = "/v1/tools/{tool_name}:invoke"
    tool_invoke_prefix: str = "/v1/tools/"
    tool_invoke_suffix: str = ":invoke"
    websocket: str = "/ws/tools"
    health: str = "/health"


MCP_URLS = MCPURLs()
