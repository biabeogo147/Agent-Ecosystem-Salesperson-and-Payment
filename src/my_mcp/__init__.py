from pathlib import Path

PACKAGE_ROOT = Path(__file__).parent.resolve()

from .urls import MCP_WEBSOCKET_PATH

__all__ = ["PACKAGE_ROOT", "MCP_WEBSOCKET_PATH"]