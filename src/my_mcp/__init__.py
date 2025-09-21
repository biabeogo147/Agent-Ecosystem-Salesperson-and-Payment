"""Utilities for interacting with the MCP service."""

from __future__ import annotations

from urllib.parse import urljoin

from config import MCP_SERVER_HOST, MCP_SERVER_PORT

MCP_BASE_URL = f"http://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}/"
MCP_API_PREFIX = "mcp/"


def build_mcp_url(path: str) -> str:
    """Return an absolute URL pointing to the MCP service."""

    return urljoin(MCP_BASE_URL, path)


__all__ = ["MCP_BASE_URL", "MCP_API_PREFIX", "build_mcp_url"]
