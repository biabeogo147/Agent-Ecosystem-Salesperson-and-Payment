"""Utilities for exposing MCP tools over HTTP."""

from pathlib import Path

from .api import create_app

PATH_TO_MCP_SERVER = Path(__file__).parent.joinpath("server.py").resolve()


def create_fastapi_app(*args, **kwargs):
    from .server import create_fastapi_app as factory

    return factory(*args, **kwargs)


__all__ = ["create_app", "create_fastapi_app", "PATH_TO_MCP_SERVER"]
