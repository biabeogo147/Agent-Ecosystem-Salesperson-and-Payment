"""Elasticsearch search operations for products (async)."""

from src.config import ELASTIC_INDEX
from src.data.elasticsearch.connection import es_connection
from src.data.redis.cache_ops import get_cached_value, set_cached_value
from src.data.redis.cache_keys import CacheKeys, TTL
from src.utils.logger import get_current_logger

logger = get_current_logger()


async def find_products_by_text(
    query_string: str,
    min_price: float = None,
    max_price: float = None,
    merchant_id: int = None,
    limit: int = 20
) -> list[dict]:
    """
    Find products by fuzzy or full-text match using Elasticsearch (async).

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
        cached = await get_cached_value(cache_key)
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

    if min_price or max_price:
        price_range = {}
        if min_price:
            price_range["gte"] = min_price
        if max_price:
            price_range["lte"] = max_price
        query["query"]["bool"]["filter"].append({"range": {"price": price_range}})

    if merchant_id is not None:
        query["query"]["bool"]["filter"].append({"term": {"merchant_id": merchant_id}})

    response = await es.search(index=ELASTIC_INDEX, body=query)

    results = []
    for hit in response.get("hits", {}).get("hits", []):
        source = hit.get("_source", {})
        results.append({
            "sku": source.get("sku", ""),
            "name": source.get("name", ""),
            "price": source.get("price", 0.0),
            "currency": source.get("currency", "USD"),
            "stock": source.get("stock", 0),
            "merchant_id": source.get("merchant_id"),
            "score": hit.get("_score", 0.0),
        })

    logger.info(f"Elasticsearch search returned {len(results)} results for query: '{query_string}'")

    try:
        await set_cached_value(cache_key, results, ttl=TTL.SEARCH)
        logger.debug(f"Cached search results: {cache_key}")
    except Exception as e:
        logger.warning(f"Failed to cache search results: {e}")

    return results


async def get_product_by_sku(sku: str) -> dict | None:
    """
    Get a single product from Elasticsearch by SKU (async).

    Args:
        sku: Product SKU

    Returns:
        Product dictionary if found, None otherwise
    """
    es = es_connection.get_client()

    try:
        response = await es.get(index=ELASTIC_INDEX, id=sku)
        if response["found"]:
            return response["_source"]
    except Exception as e:
        logger.warning(f"Product {sku} not found in Elasticsearch: {e}")

    return None
