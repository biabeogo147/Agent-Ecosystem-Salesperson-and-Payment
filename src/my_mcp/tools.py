from utils.response_format import ResponseFormat

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