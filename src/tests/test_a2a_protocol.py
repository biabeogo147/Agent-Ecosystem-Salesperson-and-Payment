import asyncio

from merchant_agent.mcp_client import MCPServiceClient
from merchant_agent.rule_based import RuleBasedMerchantAgent
from shopping_agent.rule_based import RuleBasedShoppingAgent
from data import get_product_list
from a2a.session import ShoppingA2ASession
from my_mcp.service import create_app as create_mcp_app


def test_a2a_workflow_completes_successfully():
    inventory = get_product_list()
    snapshot = {sku: product["stock"] for sku, product in inventory.items()}

    async def _run():
        mcp_client = MCPServiceClient(transport=create_mcp_app())
        customer = RuleBasedShoppingAgent(
            desired_sku="SKU001",
            quantity=2,
            shipping_weight=0.5,
            shipping_distance=10.0,
        )
        merchant = RuleBasedMerchantAgent(mcp_client=mcp_client)
        session = ShoppingA2ASession(customer=customer, merchant=merchant)

        try:
            transcript = await session.start()
        finally:
            for sku, stock in snapshot.items():
                inventory[sku]["stock"] = stock

        return transcript, customer

    transcript, customer = asyncio.run(_run())

    intents = [msg.content.get("intent") for msg in transcript if isinstance(msg.content, dict)]

    assert customer.purchase_confirmed is True
    assert "confirm_order" in intents
    assert intents[-1] == "acknowledge"
    summary = customer.order_summary
    assert summary is not None
    assert summary["sku"] == "SKU001"
    assert summary["quantity"] == 2


def test_a2a_workflow_handles_missing_product():
    inventory = get_product_list()
    snapshot = {sku: product["stock"] for sku, product in inventory.items()}

    async def _run():
        mcp_client = MCPServiceClient(transport=create_mcp_app())
        customer = RuleBasedShoppingAgent(
            desired_sku="INVALID_SKU",
            quantity=1,
            shipping_weight=1.0,
            shipping_distance=5.0,
        )
        merchant = RuleBasedMerchantAgent(mcp_client=mcp_client)
        session = ShoppingA2ASession(customer=customer, merchant=merchant)

        try:
            transcript = await session.start()
        finally:
            for sku, stock in snapshot.items():
                inventory[sku]["stock"] = stock

        return transcript, customer

    transcript, customer = asyncio.run(_run())

    intents = [msg.content.get("intent") for msg in transcript if isinstance(msg.content, dict)]

    assert customer.purchase_confirmed is False
    assert "confirm_order" not in intents
    assert "terminate" in intents
    assert intents[-1] == "acknowledge"
