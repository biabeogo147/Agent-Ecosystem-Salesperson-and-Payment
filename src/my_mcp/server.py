import json
import asyncio
from typing import Any

from my_mcp.tools import *

from mcp import types as mcp_types
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel import Server, NotificationOptions

from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool import adk_to_mcp_tool_type


print("Initializing ADK tool...")
find_product_tool = FunctionTool(find_product)
calc_shipping_tool = FunctionTool(calc_shipping)
reserve_stock_tool = FunctionTool(reserve_stock)
ADK_TOOLS = {
    find_product_tool.name: find_product_tool,
    calc_shipping_tool.name: calc_shipping_tool,
    reserve_stock_tool.name: reserve_stock_tool,
}
for adk_tool in ADK_TOOLS.values():
    print(f"ADK tool '{adk_tool.name}' initialized and ready to be exposed via MCP.")

my_mcp_server = Server("shop_mcp")


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


async def run_mcp_stdio_server():
    """Runs the MCP server, listening for connections over standard input/output."""
    # Use the stdio_server context manager from the mcp.server.stdio library
    async with stdio_server() as (read_stream, write_stream):
        print("MCP Stdio Server: Starting handshake with client...")
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
        print("MCP Stdio Server: Run loop finished or client disconnected.")


if __name__ == "__main__":
    print("Launching MCP Server to expose ADK tools via stdio...")
    try:
        asyncio.run(run_mcp_stdio_server())
    except KeyboardInterrupt:
        print("\nMCP Server (stdio) stopped by user.")
    except Exception as e:
        print(f"MCP Server (stdio) encountered an error: {e}")
    finally:
        print("MCP Server (stdio) process exiting.")