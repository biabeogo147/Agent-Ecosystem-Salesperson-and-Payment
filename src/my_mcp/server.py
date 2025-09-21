import json
from typing import Any

from fastapi import FastAPI, Request
from mcp.server.sse import SseServerTransport
from starlette.routing import Mount

from config import *
from my_mcp.logging_middleware import LoggingMiddleware
from my_mcp.tools import *

from mcp import types as mcp_types
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel import Server, NotificationOptions

from google.adk.tools.mcp_tool import adk_to_mcp_tool_type

my_mcp_server = Server("merchant_mcp")


@my_mcp_server.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    """Expose ADK tools to MCP as mcp_types.Tool list."""
    print("MCP Server: Received list_tools request.")
    exposed: list[mcp_types.Tool] = []

    for _, adk_tool in ADK_TOOLS.items():
        try:
            mcp_tool = adk_to_mcp_tool_type(adk_tool)
            print(f"MCP Server: Advertising tool: {mcp_tool.name}")
            exposed.append(mcp_tool)
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f"[WARN] Failed to convert ADK tool '{getattr(adk_tool,'name',repr(adk_tool))}': {e}")

    return exposed


@my_mcp_server.call_tool()
async def call_mcp_tool(name: str, arguments: dict | None) -> list[mcp_types.Content]:
    """Execute an exposed ADK tool by name and return MCP Content parts."""
    print(f"MCP Server: Received call_tool request for '{name}' with args: {arguments}")

    arguments = arguments or {}

    adk_tool = ADK_TOOLS.get(name)
    if not adk_tool:
        err = {"error": f"Tool '{name}' not implemented by this server."}
        print(f"MCP Server: {err['error']}")
        return [mcp_types.TextContent(type="text", text=json.dumps(err))]

    try:
        if hasattr(adk_tool, "run_async"):
            result: Any = await adk_tool.run_async(args=arguments, tool_context=None)
        else:
            result: Any = adk_tool.run(args=arguments, tool_context=None)
    except TypeError:
        try:
            if hasattr(adk_tool, "run_async"):
                result: Any = await adk_tool.run_async(**arguments)
            else:
                result: Any = adk_tool.run(**arguments)
        except Exception as e:
            error_text = json.dumps({"error": f"Failed to execute tool '{name}': {str(e)}"})
            print(f"MCP Server: {error_text}")
            return [mcp_types.TextContent(type="text", text=error_text)]
    except Exception as e:
        error_text = json.dumps({"error": f"Failed to execute tool '{name}': {str(e)}"})
        print(f"MCP Server: {error_text}")
        return [mcp_types.TextContent(type="text", text=error_text)]

    print(f"MCP Server: Tool '{name}' executed successfully.")
    return [mcp_types.TextContent(type="text", text=result)]

app = FastAPI(title="Merchant MCP")
app.add_middleware(LoggingMiddleware)


# By default, most MCP clients expect GET /sse and POST /message for SSE transport.
# SseServerTransport will advertise the /message URL back to the client.
sse = SseServerTransport("/message")

# POST /message (client -> server JSON-RPC)
app.routes.append(Mount("/message", app=sse.handle_post_message))

# GET /sse (server -> client event-stream)
@app.get("/sse")
async def sse_endpoint(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await my_mcp_server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=my_mcp_server.name,
                server_version="0.1.0",
                capabilities=my_mcp_server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
    return {"status": "disconnected"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=MCP_SERVER_PORT,
        reload=False,
    )