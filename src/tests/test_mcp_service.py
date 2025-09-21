import asyncio

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient

from merchant_agent.mcp_client import MCPServiceClient, MCPServiceError
from my_mcp.api import create_app
from my_mcp.server import create_fastapi_app
from utils.status import Status
from utils.urls import MCP_URLS


def test_mcp_client_can_list_and_invoke_tools():
    async def _run():
        client = MCPServiceClient(transport=create_app())
        tools = await client.list_tools()
        invocation = await client.call_tool("find_product", {"query": "SKU001"})
        return tools, invocation

    tools, invocation = asyncio.run(_run())

    assert any(tool["name"] == "find_product" for tool in tools)
    assert invocation["status"] == Status.SUCCESS.value
    data = invocation["data"]
    assert data["tool"] == "find_product"
    result = data["result"]
    assert isinstance(result, dict)
    assert result["status"] == Status.SUCCESS.value
    assert result["data"]


def test_mcp_client_raises_for_unknown_tool():
    async def _run():
        client = MCPServiceClient(transport=create_app())
        await client.call_tool("nonexistent", {})

    with pytest.raises(MCPServiceError):
        asyncio.run(_run())


def test_mcp_websocket_interface():
    app = create_fastapi_app()
    with TestClient(app) as client:
        with client.websocket_connect(MCP_URLS.websocket) as websocket:
            websocket.send_json({"action": "list_tools"})
            list_response = websocket.receive_json()
            assert list_response["status_code"] == 200
            payload = list_response["body"]
            assert payload["status"] == Status.SUCCESS.value
            websocket.send_json(
                {
                    "action": "invoke_tool",
                    "name": "find_product",
                    "arguments": {"query": "SKU001"},
                }
            )
            invoke_response = websocket.receive_json()
            assert invoke_response["status_code"] == 200
            invoke_body = invoke_response["body"]
            assert invoke_body["status"] == Status.SUCCESS.value
            websocket.send_text("not-json")
            error_response = websocket.receive_json()
            assert error_response["status_code"] == 400
            error_body = error_response["body"]
            assert error_body["status"] == Status.INVALID_JSON.value
