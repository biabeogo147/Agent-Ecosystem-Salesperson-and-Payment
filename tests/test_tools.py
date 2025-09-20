from src.utils import Status


def test_find_product_by_sku():
    from src.tools import find_product

    # Test case 1: Valid SKU
    response = find_product("SKU001")
    assert response.status == Status.SUCCESS
    assert response.data[0].key == "SKU001"

    # Test case 2: Invalid SKU
    response = find_product("INVALID_SKU")
    assert response.status == Status.SUCCESS
    assert response.data == []

    # Test case 3: Empty SKU
    response = find_product("")
    assert response.status == Status.SUCCESS
    assert response.data == []


def test_calc_shipping():
    from src.tools import calc_shipping

    # Test case 1: Standard case
    response = calc_shipping(10, 100)
    assert response.status == Status.SUCCESS

    # Test case 2: Zero weight
    response = calc_shipping(0, 100)
    assert response.status == Status.SUCCESS

    # Test case 3: Zero distance
    response = calc_shipping(10, 0)
    assert response.status == Status.SUCCESS

    # Test case 4: Zero weight and distance
    response = calc_shipping(0, 0)
    assert response.status == Status.SUCCESS

    # Test case 5: Large values
    response = calc_shipping(100, 1000)
    assert response.status == Status.SUCCESS