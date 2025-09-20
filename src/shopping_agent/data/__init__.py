with open("shopping_agent/data/products.json", "r") as file:
    import json
    lst_product = json.load(file)


def get_product_list() -> list:
    return lst_product