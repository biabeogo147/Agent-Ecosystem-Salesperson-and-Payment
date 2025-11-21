from src.config import ELASTIC_INDEX
from src.data.db_connection import db_connection
from src.data.es_connection import es_connection
from src.data.models.db_entity.product import Product


def find_products_list_by_substring(query_string: str, min_price: float = None, max_price: float = None):
    """
    Find products by fuzzy or full-text match using Elasticsearch.
    """
    es = es_connection

    query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query_string,
                            "fields": ["name^3", "sku^2"],
                            "fuzziness": "AUTO"
                        }
                    }
                ],
                "filter": []
            }
        },
        "size": 20
    }

    if min_price or max_price:
        price_range = {}
        if min_price:
            price_range["gte"] = min_price
        if max_price:
            price_range["lte"] = max_price
        query["query"]["bool"]["filter"].append({"range": {"price": price_range}})

    response = es.search(index=ELASTIC_INDEX, body=query)
    results = [
        {
            "sku": hit["_source"]["sku"],
            "name": hit["_source"]["name"],
            "price": hit["_source"]["price"],
            "currency": hit["_source"]["currency"],
            "stock": hit["_source"]["stock"],
            "score": hit["_score"],
        }
        for hit in response["hits"]["hits"]
    ]

    print(f"Results from Elasticsearch ({len(results)}):", results)
    return results


def find_product_by_sku(sku: str) -> Product | None:
    """
    Find a product by its SKU in DB.
    """
    db = db_connection
    product_data = db.products.find_one({"sku": sku})
    if product_data:
        return Product(**product_data)
    return None


def update_product_stock(sku: str, new_stock: int) -> bool:
    """
    Update the stock of a product by its SKU in DB.
    """
    db = db_connection
    result = db.products.update_one({"sku": sku}, {"$set": {"stock": new_stock}})
    return result.modified_count > 0