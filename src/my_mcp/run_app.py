"""Runtime helper for launching the MCP FastAPI application."""

from __future__ import annotations

import os
from typing import Tuple

import uvicorn

from .controller import app


def _load_config() -> Tuple[str, int, str]:
    host = os.environ.get("MCP_SERVICE_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_SERVICE_PORT", "8000"))
    log_level = os.environ.get("LOG_LEVEL", "info").lower()
    return host, port, log_level


def run() -> None:  # pragma: no cover - exercised in deployment
    host, port, log_level = _load_config()
    uvicorn.run(app, host=host, port=port, log_level=log_level)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    run()


__all__ = ["run"]
