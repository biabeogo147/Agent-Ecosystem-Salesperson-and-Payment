from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool import adk_to_mcp_tool_type
from mcp import types as mcp_types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from my_mcp.tools import calc_shipping, find_product, reserve_stock
from my_mcp.urls import MCP_WEBSOCKET_PATH, router

logger = logging.getLogger(__name__)

find_product_tool = FunctionTool(find_product)
calc_shipping_tool = FunctionTool(calc_shipping)
reserve_stock_tool = FunctionTool(reserve_stock)
ADK_TOOLS = {
    find_product_tool.name: find_product_tool,
    calc_shipping_tool.name: calc_shipping_tool,
    reserve_stock_tool.name: reserve_stock_tool,
}

my_mcp_server = Server("shop_mcp")


@my_mcp_server.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    """Expose ADK tools to MCP as mcp_types.Tool list."""
    logger.debug("MCP Server: list_tools requested")
    exposed: list[mcp_types.Tool] = []

    for adk_tool in ADK_TOOLS.values():
        try:
            mcp_tool = adk_to_mcp_tool_type(adk_tool)
            exposed.append(mcp_tool)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Failed to convert ADK tool '%s': %s", getattr(adk_tool, "name", adk_tool), exc)

    return exposed


@my_mcp_server.call_tool()
async def call_mcp_tool(name: str, arguments: dict | None) -> list[mcp_types.Content]:
    """Execute an exposed ADK tool by name and return MCP Content parts."""
    logger.debug("MCP Server: call_tool '%s' with args %s", name, arguments)

    arguments = arguments or {}

    adk_tool = ADK_TOOLS.get(name)
    if not adk_tool:
        error = {"error": f"Tool '{name}' not implemented by this server."}
        logger.warning("MCP Server: %s", error["error"])
        return [mcp_types.TextContent(type="text", text=json.dumps(error))]

    try:
        if hasattr(adk_tool, "run_async"):
            result: Any = await adk_tool.run_async(args=arguments, tool_context=None)
        else:
            result = adk_tool.run(args=arguments, tool_context=None)
    except TypeError:
        try:
            if hasattr(adk_tool, "run_async"):
                result = await adk_tool.run_async(**arguments)
            else:
                result = adk_tool.run(**arguments)
        except Exception as exc:  # pragma: no cover - defensive logging
            error_text = json.dumps({"error": f"Failed to execute tool '{name}': {exc}"})
            logger.exception("MCP Server: %s", error_text)
            return [mcp_types.TextContent(type="text", text=error_text)]
    except Exception as exc:  # pragma: no cover - defensive logging
        error_text = json.dumps({"error": f"Failed to execute tool '{name}': {exc}"})
        logger.exception("MCP Server: %s", error_text)
        return [mcp_types.TextContent(type="text", text=error_text)]

    logger.debug("MCP Server: tool '%s' executed successfully", name)
    return [mcp_types.TextContent(type="text", text=result)]


class _WebSocketReceiveStream:
    """Adapter that turns a FastAPI WebSocket into a byte receive stream."""

    def __init__(self, websocket: WebSocket) -> None:
        self._websocket = websocket

    async def receive(self, max_bytes: int | None = None) -> bytes:  # noqa: D401 - interface defined by MCP
        try:
            return await self._websocket.receive_bytes()
        except RuntimeError:
            try:
                text = await self._websocket.receive_text()
            except WebSocketDisconnect:
                return b""
            return text.encode("utf-8")
        except WebSocketDisconnect:
            return b""

    async def aclose(self) -> None:
        try:
            await self._websocket.close()
        except RuntimeError:
            pass


class _WebSocketSendStream:
    """Adapter that turns a FastAPI WebSocket into a byte send stream."""

    def __init__(self, websocket: WebSocket) -> None:
        self._websocket = websocket

    async def send(self, data: bytes) -> None:  # noqa: D401 - interface defined by MCP
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            await self._websocket.send_bytes(data)
        else:
            await self._websocket.send_text(text)

    async def aclose(self) -> None:
        try:
            await self._websocket.close()
        except RuntimeError:
            pass


@router.websocket(MCP_WEBSOCKET_PATH)
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle MCP traffic over a FastAPI WebSocket connection."""
    await websocket.accept()
    receive_stream = _WebSocketReceiveStream(websocket)
    send_stream = _WebSocketSendStream(websocket)

    try:
        await my_mcp_server.run(
            receive_stream,
            send_stream,
            InitializationOptions(
                server_name=my_mcp_server.name,
                server_version="0.1.0",
                capabilities=my_mcp_server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
    except WebSocketDisconnect:
        logger.info("MCP client disconnected")
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Unexpected MCP server error: %s", exc)
    finally:
        await send_stream.aclose()
        await receive_stream.aclose()


app = FastAPI(title="Shop MCP Server")
app.include_router(router)


def create_app() -> FastAPI:
    """FastAPI application factory used by uvicorn."""
    return app


if __name__ == "__main__":
    from config import MCP_SERVER_HOST, MCP_SERVER_PORT
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(
        "my_mcp.server:create_app",
        host=MCP_SERVER_HOST,
        port=MCP_SERVER_PORT,
        factory=True,
    )
