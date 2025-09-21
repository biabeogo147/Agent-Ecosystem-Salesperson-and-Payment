import asyncio
import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("fastapi.testclient")
pytest.importorskip("websockets")
from fastapi.testclient import TestClient
from websockets.server import serve

from merchant_agent.mcp_client import MCPServiceClient, MCPServiceError
from my_mcp.service import create_app
from my_mcp.controller import create_fastapi_app
from utils.status import Status
from my_mcp.urls import MCP_URLS


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


@pytest.mark.asyncio
async def test_mcp_client_uses_websocket_transport():
    service = create_app()

    async def _handler(websocket):
        async for raw_message in websocket:
            payload = json.loads(raw_message)
            action = payload.get("action")
            if action == "list_tools":
                status_code, body = await service.list_tools()
            elif action == "invoke_tool":
                tool_name = payload.get("name", "")
                arguments = payload.get("arguments") or {}
                status_code, body = await service.invoke_tool(tool_name, dict(arguments))
            else:
                status_code, body = (
                    400,
                    {
                        "status": Status.INVALID_REQUEST.value,
                        "message": "Unsupported action.",
                        "data": {"action": action},
                    },
                )
            await websocket.send(json.dumps({"status_code": status_code, "body": body}))

    server = await serve(_handler, "127.0.0.1", 0, path=MCP_URLS.websocket)
    try:
        port = server.sockets[0].getsockname()[1]
        client = MCPServiceClient(base_url=f"http://127.0.0.1:{port}")
        tools = await client.list_tools()
        assert any(tool["name"] == "find_product" for tool in tools)
        invocation = await client.call_tool("find_product", {"query": "SKU001"})
        assert invocation["status"] == Status.SUCCESS.value
    finally:
        server.close()
        await server.wait_closed()
