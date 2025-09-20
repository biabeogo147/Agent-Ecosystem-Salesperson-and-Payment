def test_find_product_by_sku():
    from my_mcp.tools import find_product

    # Test case 1: Valid SKU
    response = find_product("SKU001")
    print(response)

    # Test case 2: Invalid SKU
    response = find_product("INVALID_SKU")
    print(response)

    # Test case 3: Empty SKU
    response = find_product("")
    print(response)


def test_calc_shipping():
    from my_mcp.tools import calc_shipping

    # Test case 1: Standard case
    response = calc_shipping(10, 100)
    print(response)

    # Test case 2: Zero weight
    response = calc_shipping(0, 100)
    print(response)

    # Test case 3: Zero distance
    response = calc_shipping(10, 0)
    print(response)

    # Test case 4: Zero weight and distance
    response = calc_shipping(0, 0)
    print(response)

    # Test case 5: Large values
    response = calc_shipping(100, 1000)
    print(response)