from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from my_agent.salesperson_agent.salesperson_mcp_client import (
    SalespersonMcpClient,
    prepare_calc_shipping,
    prepare_calc_shipping_with_client,
    prepare_find_product_with_client,
    prepare_reserve_stock,
    prepare_reserve_stock_with_client,
)
from utils.status import Status


@pytest.mark.asyncio
async def test_find_product_by_sku() -> None:
    from my_mcp.salesperson.tools_for_salesperson_agent import find_product

    results = await asyncio.gather(
        find_product("SKU0001"),
        find_product("INVALID_SKU"),
        find_product(""),
    )

    print(results[0])
    print(results[1])
    print(results[2])


@pytest.mark.asyncio
async def test_calc_shipping() -> None:
    from my_mcp.salesperson.tools_for_salesperson_agent import calc_shipping

    results = await asyncio.gather(
        calc_shipping(10, 100),
        calc_shipping(0, 100),
        calc_shipping(10, 0),
        calc_shipping(0, 0),
    )

    print(results[0])
    print(results[1])
    print(results[2])
    print(results[3])


@pytest.mark.asyncio
async def test_reserve_stock() -> None:
    from my_mcp.salesperson.tools_for_salesperson_agent import reserve_stock

    results = await asyncio.gather(
        reserve_stock("SKU0001", 5),
        reserve_stock("SKU0001", 90),
        reserve_stock("INVALID_SKU", 1),
        reserve_stock("SKU0002", 100),
    )

    print(results[0])
    print(results[1])
    print(results[2])
    print(results[3])


@pytest.mark.asyncio
async def test_salesperson_client_find_product_delegates_to_json_call() -> None:
    client = SalespersonMcpClient(base_url="http://example.com")
    client._call_tool_json = AsyncMock(
        return_value={"status": Status.SUCCESS.value, "message": "SUCCESS", "data": []}
    )

    result = await client.find_product(query="shoes")

    client._call_tool_json.assert_awaited_once_with(
        "find_product", {"query": "shoes"}
    )
    assert result == {"status": Status.SUCCESS.value, "message": "SUCCESS", "data": []}


@pytest.mark.asyncio
async def test_salesperson_client_find_product_rejects_non_dict_payload() -> None:
    client = SalespersonMcpClient(base_url="http://example.com")
    client._call_tool_json = AsyncMock(
        return_value=["unexpected"]
    )

    with pytest.raises(RuntimeError):
        await client.find_product(query="invalid")


@pytest.mark.asyncio
async def test_salesperson_client_calc_shipping_delegates_to_json_call() -> None:
    client = SalespersonMcpClient(base_url="http://example.com")
    client._call_tool_json = AsyncMock(
        return_value={"status": Status.SUCCESS.value, "message": "SUCCESS", "data": 15.5}
    )

    result = await client.calc_shipping(weight=2.5, distance=10.0)

    client._call_tool_json.assert_awaited_once_with(
        "calc_shipping", {"weight": 2.5, "distance": 10.0}
    )
    assert result == {"status": Status.SUCCESS.value, "message": "SUCCESS", "data": 15.5}


@pytest.mark.asyncio
async def test_salesperson_client_reserve_stock_delegates_to_json_call() -> None:
    client = SalespersonMcpClient(base_url="http://example.com")
    client._call_tool_json = AsyncMock(
        return_value={"status": Status.SUCCESS.value, "message": "SUCCESS", "data": True}
    )

    result = await client.reserve_stock(sku="SKU0123", quantity=3)

    client._call_tool_json.assert_awaited_once_with(
        "reserve_stock", {"sku": "SKU0123", "quantity": 3}
    )
    assert result == {"status": Status.SUCCESS.value, "message": "SUCCESS", "data": True}


@pytest.mark.asyncio
async def test_find_product_wrapper_uses_provided_client() -> None:
    fake_client = AsyncMock(spec=SalespersonMcpClient)
    fake_client.find_product.return_value = {
        "status": Status.SUCCESS.value,
        "message": "SUCCESS",
        "data": [],
    }

    result = await prepare_find_product_with_client("hat", client=fake_client)

    fake_client.find_product.assert_awaited_once_with(query="hat")
    assert result == {
        "status": Status.SUCCESS.value,
        "message": "SUCCESS",
        "data": [],
    }


@pytest.mark.asyncio
async def test_calc_shipping_wrapper_defaults_to_singleton() -> None:
    fake_client = AsyncMock(spec=SalespersonMcpClient)
    fake_client.calc_shipping.return_value = {
        "status": Status.SUCCESS.value,
        "message": "SUCCESS",
        "data": 9.0,
    }

    with patch(
        "my_agent.salesperson_agent.salesperson_mcp_client.get_salesperson_mcp_client",
        return_value=fake_client,
    ):
        result = await prepare_calc_shipping(1.0, 5.0)

    fake_client.calc_shipping.assert_awaited_once_with(weight=1.0, distance=5.0)
    assert result == {
        "status": Status.SUCCESS.value,
        "message": "SUCCESS",
        "data": 9.0,
    }


@pytest.mark.asyncio
async def test_reserve_stock_wrapper_defaults_to_singleton() -> None:
    fake_client = AsyncMock(spec=SalespersonMcpClient)
    fake_client.reserve_stock.return_value = {
        "status": Status.SUCCESS.value,
        "message": "SUCCESS",
        "data": True,
    }

    with patch(
        "my_agent.salesperson_agent.salesperson_mcp_client.get_salesperson_mcp_client",
        return_value=fake_client,
    ):
        result = await prepare_reserve_stock("SKU0001", 2)

    fake_client.reserve_stock.assert_awaited_once_with(sku="SKU0001", quantity=2)
    assert result == {
        "status": Status.SUCCESS.value,
        "message": "SUCCESS",
        "data": True,
    }
