import asyncio

from src.config import ELASTIC_INDEX
from src.data.elasticsearch.connection import es_connection
from src.data.redis.cache_ops import get_cached_value, set_cached_value
from src.data.redis.cache_keys import CacheKeys, TTL
from src.utils.logger import get_current_logger

logger = get_current_logger()


async def _cache_search_results(cache_key: str, results: list):
    """Background task to cache search results."""
    try:
        await set_cached_value(cache_key, results, ttl=TTL.SEARCH)
        logger.debug(f"Cached search results: {cache_key}")
    except Exception as e:
        logger.warning(f"Failed to cache search results: {e}")


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

    normalized_query = (query_string or "").strip()
    sku_candidate = normalized_query.replace(" ", "").upper()

    filters: list[dict] = []

    if min_price is not None or max_price is not None:
        price_range: dict = {}
        if min_price is not None:
            price_range["gte"] = min_price
        if max_price is not None:
            price_range["lte"] = max_price
        filters.append({"range": {"price": price_range}})

    if merchant_id is not None:
        filters.append({"term": {"merchant_id": merchant_id}})

    # 4. Build should clauses: name + sku
    should_clauses: list[dict] = []

    # 4.1. Full-text trên name + name.autocomplete
    if normalized_query:
        should_clauses.append(
            {
                "multi_match": {
                    "query": normalized_query,
                    "fields": [
                        "name^3",               # name được boost
                        "name.autocomplete^4",  # autocomplete được boost mạnh hơn
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                    "operator": "and",       # bắt "iphone 15 pro" đầy đủ hơn
                }
            }
        )

    # 4.2. Exact SKU (case-insensitive, bỏ khoảng trắng)
    # Điều kiện độ dài ≥ 4 để tránh query linh tinh (vd: "ip")
    if sku_candidate and len(sku_candidate) >= 4:
        should_clauses.append(
            {
                "term": {
                    "sku": sku_candidate 
                }
            }
        )

    # Nếu muốn cho phép match SKU kiểu *IPHONE15PRO* thì có thể thêm:
    # should_clauses.append(
    #     {
    #         "wildcard": {
    #             "sku": f"*{sku_candidate}*"
    #         }
    #     }
    # )

    query = {
        "query": {
            "bool": {
                "filter": filters,
                "should": should_clauses,
                "minimum_should_match": 1
            }
        },
        "size": limit
    }

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

    asyncio.create_task(_cache_search_results(cache_key, results))

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
