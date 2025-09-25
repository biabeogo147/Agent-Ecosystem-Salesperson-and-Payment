from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams
from google.adk.tools.mcp_tool import StreamableHTTPConnectionParams, McpToolset


def get_mcp_sse_connect_params(url: str, token: str) -> SseConnectionParams:
    """Get MCP SSE connection params"""
    headers = {"Authorization": f"Bearer {token}"}
    return SseConnectionParams(
        url=url,
        headers=headers or None,
        timeout=30,
        sse_read_timeout=120,
    )


def get_mcp_streamable_http_connect_params(url: str, token: str) -> StreamableHTTPConnectionParams:
    """Get MCP Streamable Http connection params"""
    headers = {"Authorization": f"Bearer {token}"}
    return StreamableHTTPConnectionParams(
        headers=headers or None,
        timeout=30,
        url=url,
    )


def get_mcp_toolset(url: str, token: str) -> McpToolset:
    """Get MCP Toolset"""
    # Using StreamableHTTPConnectionParams
    return McpToolset(
        connection_params=get_mcp_streamable_http_connect_params(url, token)
    )



