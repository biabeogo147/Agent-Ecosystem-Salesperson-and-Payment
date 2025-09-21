"""Utilities for exposing MCP tools over HTTP."""

from pathlib import Path

from .service import create_app

PATH_TO_MCP_SERVER = Path(__file__).parent.joinpath("run_app.py").resolve()


def create_fastapi_app(*args, **kwargs):
    from .controller import create_fastapi_app as factory

    return factory(*args, **kwargs)


__all__ = ["create_app", "create_fastapi_app", "PATH_TO_MCP_SERVER"]
