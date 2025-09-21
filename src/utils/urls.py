"""Centralised URL definitions for service endpoints."""

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
    health: str = "/healthz"


@dataclass(frozen=True)
class ShoppingURLs:
    """URL mapping for the shopping session orchestrator."""

    health: str = "/healthz"
    sessions: str = "/v1/sessions"


MCP_URLS = MCPURLs()
SHOPPING_URLS = ShoppingURLs()

__all__ = ["MCP_URLS", "SHOPPING_URLS", "MCPURLs", "ShoppingURLs"]
