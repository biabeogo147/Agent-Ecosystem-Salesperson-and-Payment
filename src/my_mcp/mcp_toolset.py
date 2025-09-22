import os

from google.adk.tools import MCPToolset
from google.adk.tools.mcp_tool import StreamableHTTPConnectionParams


def get_mcp_toolset(url: str) -> MCPToolset:
    """Get MCP Toolset"""
    headers = {}
    token = os.getenv("MCP_AUTH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Using SseConnectionParams
    # return MCPToolset(
    #     connection_params=SseConnectionParams(
    #         url=mcp_sse_url,
    #         headers=headers or None,
    #         timeout=30,
    #         sse_read_timeout=120,
    #     )
    # )

    # Using StreamableHTTPConnectionParams
    return MCPToolset(
        connection_params=StreamableHTTPConnectionParams(
            headers=headers,
            timeout=30,
            url=url,
        )
    )



