from utils.response_format import ResponseFormat


def find_product(query: str) -> dict:
    """
    Find product by SKU or substring of name.
    Returns: ResponseFormat(data: list)
    """

    from shopping_agent.data import get_product_list

    query = query.lower()
    lst_product = get_product_list()

    results = [
        v
        for k, v in lst_product.items()
        if query == v["name"].lower() or query == k.lower()
    ]

    return ResponseFormat(data=results).to_json()


def calc_shipping(weight: float, distance: float) -> dict:
    """
    Calculate shipping cost based on weight (kg) and distance (km).
    Returns: ResponseFormat(data: float)
    """
    base_cost = 5.0  # base cost in USD
    weight_factor = 1.0  # cost per kg
    distance_factor = 0.5  # cost per km

    cost = base_cost + (weight * weight_factor) + (distance * distance_factor)
    return ResponseFormat(data=round(cost, 2)).to_json()