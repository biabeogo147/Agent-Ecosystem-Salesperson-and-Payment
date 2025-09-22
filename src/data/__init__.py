import os
import json

BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "products.json")


with open(DATA_PATH, "r", encoding="utf-8") as file:
    lst_product = json.load(file)


def get_product_list() -> dict:
    return lst_product