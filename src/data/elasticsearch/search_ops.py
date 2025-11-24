"""Elasticsearch search operations for products."""

from src.config import ELASTIC_INDEX
from src.data.elasticsearch.connection import es_connection
from src.data.redis.cache_ops import get_cached_value, set_cached_value
from src.data.redis.cache_keys import CacheKeys, TTL
from src.utils.logger import logger


def find_products_by_text(
    query_string: str,
    min_price: float = None,
    max_price: float = None,
    merchant_id: int = None,
    limit: int = 20
) -> list[dict]:
    """
    Find products by fuzzy or full-text match using Elasticsearch.

    Args:
        query_string: Search query text
        min_price: Minimum price filter (optional)
        max_price: Maximum price filter (optional)
        merchant_id: Filter by merchant ID (optional)
        limit: Maximum number of results to return

    Returns:
        List of product dictionaries with relevance scores
    """
    cache_key = CacheKeys.search_products(query_string, min_price, max_price, merchant_id, limit)

    try:
        cached = get_cached_value(cache_key)
        if cached:
            logger.debug(f"Cache HIT: {cache_key}")
            return cached
    except Exception as e:
        logger.warning(f"Cache read failed for {cache_key}, using ES: {e}")

    logger.debug(f"Cache MISS: {cache_key}")
    es = es_connection.get_client()

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
        "size": limit
    }

    # Add price range filter
    if min_price or max_price:
        price_range = {}
        if min_price:
            price_range["gte"] = min_price
        if max_price:
            price_range["lte"] = max_price
        query["query"]["bool"]["filter"].append({"range": {"price": price_range}})

    # Add merchant filter
    if merchant_id is not None:
        query["query"]["bool"]["filter"].append({"term": {"merchant_id": merchant_id}})

    response = es.search(index=ELASTIC_INDEX, body=query)

    results = [
        {
            "sku": hit["_source"]["sku"],
            "name": hit["_source"]["name"],
            "price": hit["_source"]["price"],
            "currency": hit["_source"]["currency"],
            "stock": hit["_source"]["stock"],
            "merchant_id": hit["_source"]["merchant_id"],
            "score": hit["_score"],
        }
        for hit in response["hits"]["hits"]
    ]

    logger.info(f"Elasticsearch search returned {len(results)} results for query: '{query_string}'")

    try:
        set_cached_value(cache_key, results, ttl=TTL.SEARCH)
        logger.debug(f"Cached search results: {cache_key}")
    except Exception as e:
        logger.warning(f"Failed to cache search results: {e}")

    return results


def get_product_by_sku(sku: str) -> dict | None:
    """
    Get a single product from Elasticsearch by SKU.

    Args:
        sku: Product SKU

    Returns:
        Product dictionary if found, None otherwise
    """
    es = es_connection.get_client()

    try:
        response = es.get(index=ELASTIC_INDEX, id=sku)
        if response["found"]:
            return response["_source"]
    except Exception as e:
        logger.warning(f"Product {sku} not found in Elasticsearch: {e}")

    return None
