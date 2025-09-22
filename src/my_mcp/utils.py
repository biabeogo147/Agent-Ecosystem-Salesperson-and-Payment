import json
from typing import Any

from mcp import types as mcp_types
from google.adk.tools.mcp_tool import adk_to_mcp_tool_type


async def list_mcp_tools_with_dict(tool_lists: dict) -> list[mcp_types.Tool]:
    """Expose ADK tools to MCP as mcp_types.Tool list."""
    print("MCP Server: Received list_tools request.")
    exposed: list[mcp_types.Tool] = []

    for _, adk_tool in tool_lists.items():
        try:
            mcp_tool = adk_to_mcp_tool_type(adk_tool)
            print(f"MCP Server: Advertising tool: {mcp_tool.name}")
            exposed.append(mcp_tool)
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f"[WARN] Failed to convert ADK tool '{getattr(adk_tool,'name',repr(adk_tool))}': {e}")

    return exposed


async def call_mcp_tool_with_dict(name: str, arguments: dict | None, tool_lists: dict) -> list[mcp_types.Content]:
    """Execute an exposed ADK tool by name and return MCP Content parts."""
    print(f"MCP Server: Received call_tool request for '{name}' with args: {arguments}")

    arguments = arguments or {}

    adk_tool = tool_lists.get(name)
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