import asyncio

import pytest


@pytest.mark.asyncio
async def test_find_product_by_sku():
    from my_mcp.salesperson.tools_for_salesperson_agent import find_product

    r1, r2, r3 = await asyncio.gather(
        find_product("SKU001"),
        find_product("INVALID_SKU"),
        find_product(""),
    )

    print(r1)
    print(r2)
    print(r3)


@pytest.mark.asyncio
async def test_calc_shipping():
    from my_mcp.salesperson.tools_for_salesperson_agent import calc_shipping

    r1, r2, r3, r4 = await asyncio.gather(
        calc_shipping(10, 100),
        calc_shipping(0, 100),
        calc_shipping(10, 0),
        calc_shipping(0, 0),
    )

    print(r1)
    print(r2)
    print(r3)
    print(r4)


@pytest.mark.asyncio
async def test_reserve_stock():
    from my_mcp.salesperson.tools_for_salesperson_agent import reserve_stock

    r1, r2, r3, r4 = await asyncio.gather(
        reserve_stock("SKU001", 5),
        reserve_stock("SKU001", 90),
        reserve_stock("INVALID_SKU", 1),
        reserve_stock("SKU002", 100),
    )

    print(r1)
    print(r2)
    print(r3)
    print(r4)
