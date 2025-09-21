"""URL route definitions for the MCP FastAPI service."""

from __future__ import annotations

from fastapi import APIRouter, status

from my_mcp import services

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/tools", response_model=services.ToolListResponse)
async def list_tools() -> services.ToolListResponse:
    """Expose metadata about the available tools."""

    return await services.list_tools()


@router.get("/stream")
async def stream(client_id: str):
    """Establish an SSE stream for the given client identifier."""

    return await services.stream(client_id)


@router.post(
    "/tools/{tool_name}/invoke",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=services.ToolInvokeResponse,
)
async def invoke_tool(
    tool_name: str, request: services.ToolInvokeRequest
) -> services.ToolInvokeResponse:
    """Schedule tool execution and stream the result back to the caller."""

    return await services.invoke_tool(tool_name, request)
