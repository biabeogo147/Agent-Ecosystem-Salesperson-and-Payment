import asyncio


def test_find_product_by_sku():
    from my_mcp.tools import find_product

    async def _run():
        t1 = asyncio.create_task(find_product("SKU001"))
        t2 = asyncio.create_task(find_product("INVALID_SKU"))
        t3 = asyncio.create_task(find_product(""))
        return await asyncio.gather(t1, t2, t3)

    r1, r2, r3 = asyncio.run(_run())

    print(r1)
    print(r2)
    print(r3)


def test_calc_shipping():
    from my_mcp.tools import calc_shipping

    async def _run():
        t1 = asyncio.create_task(calc_shipping(10, 100))
        t2 = asyncio.create_task(calc_shipping(0, 100))
        t3 = asyncio.create_task(calc_shipping(10, 0))
        t4 = asyncio.create_task(calc_shipping(0, 0))
        return await asyncio.gather(t1, t2, t3, t4)

    r1, r2, r3, r4 = asyncio.run(_run())

    print(r1)
    print(r2)
    print(r3)
    print(r4)


def test_reserve_stock():
    from my_mcp.tools import reserve_stock

    async def _run():
        t1 = asyncio.create_task(reserve_stock("SKU001", 5))
        t2 = asyncio.create_task(reserve_stock("SKU001", 90))
        t3 = asyncio.create_task(reserve_stock("INVALID_SKU", 1))
        t4 = asyncio.create_task(reserve_stock("SKU002", 100))
        return await asyncio.gather(t1, t2, t3, t4)

    r1, r2, r3, r4 = asyncio.run(_run())

    print(r1)
    print(r2)
    print(r3)
    print(r4)
