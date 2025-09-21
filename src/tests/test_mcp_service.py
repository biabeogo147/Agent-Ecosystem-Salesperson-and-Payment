import asyncio

import pytest

from merchant_agent.mcp_client import MCPServiceClient, MCPServiceError
from my_mcp.api import create_app
from utils.status import Status


def test_mcp_client_can_list_and_invoke_tools():
    async def _run():
        client = MCPServiceClient(transport=create_app())
        tools = await client.list_tools()
        invocation = await client.call_tool("find_product", {"query": "SKU001"})
        return tools, invocation

    tools, invocation = asyncio.run(_run())

    assert any(tool["name"] == "find_product" for tool in tools)
    assert invocation["status"] == "success"
    assert invocation["tool"] == "find_product"
    result = invocation["result"]
    assert result["status"] == Status.SUCCESS.value
    assert result["data"]


def test_mcp_client_raises_for_unknown_tool():
    async def _run():
        client = MCPServiceClient(transport=create_app())
        await client.call_tool("nonexistent", {})

    with pytest.raises(MCPServiceError):
        asyncio.run(_run())
