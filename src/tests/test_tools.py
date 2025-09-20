import asyncio
import pytest


@pytest.mark.asyncio
async def test_find_product_by_sku():
    from my_mcp.tools import find_product

    t1 = asyncio.create_task(find_product("SKU001"))
    t2 = asyncio.create_task(find_product("INVALID_SKU"))
    t3 = asyncio.create_task(find_product(""))

    r1, r2, r3 = await asyncio.gather(t1, t2, t3)

    print(r1)
    print(r2)
    print(r3)


@pytest.mark.asyncio
async def test_calc_shipping():
    from my_mcp.tools import calc_shipping

    t1 = asyncio.create_task(calc_shipping(10, 100))
    t2 = asyncio.create_task(calc_shipping(0, 100))
    t3 = asyncio.create_task(calc_shipping(10, 0))
    t4 = asyncio.create_task(calc_shipping(0, 0))

    r1, r2, r3, r4 = await asyncio.gather(t1, t2, t3, t4)

    print(r1)
    print(r2)
    print(r3)
    print(r4)