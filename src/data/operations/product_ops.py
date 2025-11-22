from src.config import ELASTIC_INDEX
from src.data.db_connection import db_connection
from src.data.es_connection import es_connection
from src.data.models.db_entity.product import Product
from src.utils.logger import logger


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

    logger.info(f"Results from Elasticsearch ({len(results)}): {results}")
    return results


def find_product_by_sku(sku: str) -> Product | None:
    """
    Find a product by its SKU in DB.
    """
    session = db_connection.get_session()
    try:
        product = session.query(Product).filter(Product.sku == sku).first()
        return product
    finally:
        session.close()


def update_product_stock(sku: str, new_stock: int) -> bool:
    """
    Update the stock of a product by its SKU in DB.
    """
    session = db_connection.get_session()
    try:
        product = session.query(Product).filter(Product.sku == sku).first()
        if not product:
            return False
        product.stock = new_stock
        session.commit()
        return True
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()