import asyncio

from a2a.api import create_app as create_session_service
from merchant_agent.mcp_client import MCPServiceClient
from my_mcp.api import create_app as create_mcp_service


def _invoke_session(payload: dict):
    async def _run():
        mcp_service = create_mcp_service()
        mcp_client = MCPServiceClient(transport=mcp_service)
        session_service = create_session_service(mcp_client=mcp_client)
        return await session_service.dispatch("POST", "/v1/sessions", payload)

    return asyncio.run(_run())


def test_shopping_api_success_path():
    status, body = _invoke_session(
        {
            "sku": "SKU001",
            "quantity": 1,
            "shipping_weight": 0.5,
            "shipping_distance": 5.0,
        }
    )

    assert status == 200
    assert body["status"] == "success"
    assert body["summary"]["sku"] == "SKU001"
    assert any(
        isinstance(message["content"], dict) and message["content"].get("intent") == "confirm_order"
        for message in body["transcript"]
    )


def test_shopping_api_handles_missing_product():
    status, body = _invoke_session(
        {
            "sku": "INVALID_SKU",
            "quantity": 1,
            "shipping_weight": 0.5,
            "shipping_distance": 5.0,
        }
    )

    assert status == 200
    assert body["status"] == "failed"
    assert body["summary"] is None
    assert body["last_error"] is not None
