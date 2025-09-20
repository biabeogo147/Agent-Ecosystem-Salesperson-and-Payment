from utils.response_format import ResponseFormat
from utils.status import Status
from utils.app_string import *


async def find_product(query: str) -> str:
    """
    Find product by SKU or substring of name.
    """
    from data import get_product_list

    query = query.lower()
    lst_product = get_product_list()

    results = [
        v
        for k, v in lst_product.items()
        if query == v["name"].lower() or query == k.lower()
    ]

    return ResponseFormat(data=results).to_json()


async def calc_shipping(weight: float, distance: float) -> str:
    """
    Calculate shipping cost based on weight (kg) and distance (km).
    """
    base_cost = 5.0  # base cost in USD
    weight_factor = 1.0  # cost per kg
    distance_factor = 0.5  # cost per km

    cost = base_cost + (weight * weight_factor) + (distance * distance_factor)
    return ResponseFormat(data=round(cost, 2)).to_json()


async def reserve_stock(sku: str, quantity: int) -> str:
    """
    Reserve stock for a given SKU and quantity.
    """
    from data import get_product_list

    lst_product = get_product_list()
    product = lst_product.get(sku)

    if not product:
        return ResponseFormat(status=Status.PRODUCT_NOT_FOUND, data=False, message=PRODUCT_NOT_FOUND).to_json()

    if product["stock"] < quantity:
        return ResponseFormat(status=Status.QUANTITY_EXCEEDED, data=False, message=QUANTITY_EXCEEDED).to_json()

    product["stock"] -= quantity
    return ResponseFormat(data=True).to_json()