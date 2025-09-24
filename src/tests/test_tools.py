from __future__ import annotations

import asyncio

import pytest


@pytest.mark.asyncio
async def test_find_product_by_sku() -> None:
    from my_mcp.salesperson.tools_for_salesperson_agent import find_product

    results = await asyncio.gather(
        find_product("SKU001"),
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
        reserve_stock("SKU001", 5),
        reserve_stock("SKU001", 90),
        reserve_stock("INVALID_SKU", 1),
        reserve_stock("SKU002", 100),
    )

    print(results[0])
    print(results[1])
    print(results[2])
    print(results[3])
