"""Utilities for exposing MCP tools over HTTP."""

from pathlib import Path

from .api import create_app

PATH_TO_MCP_SERVER = Path(__file__).parent.joinpath("server.py").resolve()

__all__ = ["create_app", "PATH_TO_MCP_SERVER"]
