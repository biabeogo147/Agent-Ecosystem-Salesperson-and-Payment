from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from my_agent.salesperson_agent import product_tasks
from my_agent.salesperson_agent.salesperson_mcp_client import SalespersonMcpClient


@pytest.mark.asyncio
async def test_salesperson_client_find_product_delegates_to_json_call() -> None:
    client = SalespersonMcpClient(base_url="http://example.com")
    client._call_tool_json = AsyncMock(  # type: ignore[attr-defined]
        return_value={"status": "SUCCESS", "data": []}
    )

    result = await client.find_product(query="shoes")

    client._call_tool_json.assert_awaited_once_with(
        "find_product", {"query": "shoes"}
    )
    assert result == {"status": "SUCCESS", "data": []}


@pytest.mark.asyncio
async def test_salesperson_client_find_product_rejects_non_dict_payload() -> None:
    client = SalespersonMcpClient(base_url="http://example.com")
    client._call_tool_json = AsyncMock(  # type: ignore[attr-defined]
        return_value=["unexpected"]
    )

    with pytest.raises(RuntimeError):
        await client.find_product(query="invalid")


@pytest.mark.asyncio
async def test_salesperson_client_calc_shipping_delegates_to_json_call() -> None:
    client = SalespersonMcpClient(base_url="http://example.com")
    client._call_tool_json = AsyncMock(  # type: ignore[attr-defined]
        return_value={"status": "SUCCESS", "data": 15.5}
    )

    result = await client.calc_shipping(weight=2.5, distance=10.0)

    client._call_tool_json.assert_awaited_once_with(
        "calc_shipping", {"weight": 2.5, "distance": 10.0}
    )
    assert result == {"status": "SUCCESS", "data": 15.5}


@pytest.mark.asyncio
async def test_salesperson_client_reserve_stock_delegates_to_json_call() -> None:
    client = SalespersonMcpClient(base_url="http://example.com")
    client._call_tool_json = AsyncMock(  # type: ignore[attr-defined]
        return_value={"status": "SUCCESS", "data": True}
    )

    result = await client.reserve_stock(sku="SKU123", quantity=3)

    client._call_tool_json.assert_awaited_once_with(
        "reserve_stock", {"sku": "SKU123", "quantity": 3}
    )
    assert result == {"status": "SUCCESS", "data": True}


@pytest.mark.asyncio
async def test_find_product_wrapper_uses_provided_client() -> None:
    fake_client = AsyncMock(spec=SalespersonMcpClient)
    fake_client.find_product.return_value = {"status": "SUCCESS", "data": []}

    result = await product_tasks.find_product("hat", mcp_client=fake_client)

    fake_client.find_product.assert_awaited_once_with(query="hat")
    assert result == {"status": "SUCCESS", "data": []}


@pytest.mark.asyncio
async def test_calc_shipping_wrapper_defaults_to_singleton() -> None:
    fake_client = AsyncMock(spec=SalespersonMcpClient)
    fake_client.calc_shipping.return_value = {"status": "SUCCESS", "data": 9.0}

    with patch(
        "my_agent.salesperson_agent.product_tasks.get_salesperson_mcp_client",
        return_value=fake_client,
    ):
        result = await product_tasks.calc_shipping(1.0, 5.0)

    fake_client.calc_shipping.assert_awaited_once_with(weight=1.0, distance=5.0)
    assert result == {"status": "SUCCESS", "data": 9.0}


@pytest.mark.asyncio
async def test_reserve_stock_wrapper_defaults_to_singleton() -> None:
    fake_client = AsyncMock(spec=SalespersonMcpClient)
    fake_client.reserve_stock.return_value = {"status": "SUCCESS", "data": True}

    with patch(
        "my_agent.salesperson_agent.product_tasks.get_salesperson_mcp_client",
        return_value=fake_client,
    ):
        result = await product_tasks.reserve_stock("SKU1", 2)

    fake_client.reserve_stock.assert_awaited_once_with(sku="SKU1", quantity=2)
    assert result == {"status": "SUCCESS", "data": True}
