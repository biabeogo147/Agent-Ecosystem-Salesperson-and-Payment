from fastapi import APIRouter

MCP_WEBSOCKET_PATH = "/ws/mcp"

router = APIRouter()

__all__ = ["MCP_WEBSOCKET_PATH", "router"]
