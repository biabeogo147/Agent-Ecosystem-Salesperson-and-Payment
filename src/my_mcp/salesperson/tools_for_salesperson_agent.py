from __future__ import annotations

import uuid
import random

from google.adk.tools import FunctionTool

from . import salesperson_mcp_logger

from src.config import RETURN_URL, CANCEL_URL, EMBED_VECTOR_DIM
from src.utils.response_format import ResponseFormat
from src.utils.status import Status
from src.utils.app_string import *
from src.data.redis.cache_ops import get_cached_value, set_cached_value
from src.data.redis.cache_keys import CacheKeys, TTL
from src.data.elasticsearch.search_ops import find_products_by_text
from src.data.postgres.product_ops import find_product_by_sku, update_product_stock
from src.data.milvus.connection import get_client_instance


async def find_product(query: str) -> str:
    """
    Find product by SKU or substring of name.
    """
    import asyncio

    query = query.lower()
    results = await asyncio.to_thread(find_products_by_text, query)

    return ResponseFormat(data=results).to_json()


async def calc_shipping(weight: float, distance: float) -> str:
    """
    Calculate shipping cost based on weight (kg) and distance (km).
    """
    base_cost = 5.0         # USD
    weight_factor = 1.0     # Kg
    distance_factor = 0.5   # Km

    cost = base_cost + (weight * weight_factor) + (distance * distance_factor)
    return ResponseFormat(data=round(cost, 2)).to_json()


async def reserve_stock(sku: str, quantity: int) -> str:
    """
    Reserve stock for a given SKU and quantity.
    """
    import asyncio

    product = await asyncio.to_thread(find_product_by_sku, sku, use_cache=False)

    if not product:
        return ResponseFormat(status=Status.PRODUCT_NOT_FOUND, data=False, message=PRODUCT_NOT_FOUND).to_json()

    if product.stock < quantity:
        return ResponseFormat(status=Status.QUANTITY_EXCEEDED, data=False, message=QUANTITY_EXCEEDED).to_json()

    result = await asyncio.to_thread(update_product_stock, sku, product.stock - quantity)

    return ResponseFormat(data=result).to_json()


async def generate_context_id(prefix: str) -> str:
    """Create a unique correlation identifier used to track payment requests."""
    context_id = f"{prefix}-{uuid.uuid4()}"
    return ResponseFormat(data=context_id).to_json()


async def generate_return_url(context_id: str) -> str:
    """Build the return URL that the payment gateway should redirect to."""
    return_url = f"{RETURN_URL}?cid={context_id}"
    return ResponseFormat(data=return_url).to_json()


async def generate_cancel_url(context_id: str) -> str:
    """Build the cancel URL that the payment gateway should redirect to."""
    cancel_url = f"{CANCEL_URL}?cid={context_id}"
    return ResponseFormat(data=cancel_url).to_json()


async def search_product_documents(query: str, product_sku: str | None = None, limit: int = 5) -> str:
    """
    Search product documents in vector database.
    Args:
        query: Search query text
        product_sku: Optional product SKU to filter results
        limit: Maximum number of results (default 5)
    Returns: List of matching documents
    """
    import asyncio

    cache_key = CacheKeys.vector_search(query, product_sku, limit)

    try:
        cached = await asyncio.to_thread(get_cached_value, cache_key)
        if cached:
            salesperson_mcp_logger.debug(f"Cache HIT: {cache_key}")
            return ResponseFormat(data=cached).to_json()
    except Exception as e:
        salesperson_mcp_logger.warning(f"Cache read failed for {cache_key}, using Milvus: {e}")

    salesperson_mcp_logger.debug(f"Cache MISS: {cache_key}")

    try:
        client = await asyncio.to_thread(get_client_instance)

        # Generate mock embedding for query (replace with real embedding in production)
        random.seed(hash(query) % (2**32))
        query_embedding = [random.uniform(-1, 1) for _ in range(EMBED_VECTOR_DIM)]

        search_params = {
            "collection_name": "Document",
            "data": [query_embedding],
            "anns_field": "embedding",
            "limit": limit,
            "output_fields": ["id", "text", "title", "product_sku", "chunk_id"],
        }

        # Add filter if product_sku is provided
        if product_sku:
            search_params["filter"] = f'product_sku == "{product_sku}"'

        results = await asyncio.to_thread(client.search, **search_params)

        documents = []
        for hits in results:
            for hit in hits:
                documents.append({
                    "id": hit.get("id"),
                    "text": hit.get("entity", {}).get("text", ""),
                    "title": hit.get("entity", {}).get("title", ""),
                    "product_sku": hit.get("entity", {}).get("product_sku", ""),
                    "chunk_id": hit.get("entity", {}).get("chunk_id"),
                    "score": hit.get("distance", 0),
                })

        try:
            await asyncio.to_thread(set_cached_value, cache_key, documents, ttl=TTL.VECTOR_SEARCH)
            salesperson_mcp_logger.debug(f"Cached vector search results: {cache_key}")
        except Exception as e:
            salesperson_mcp_logger.warning(f"Failed to cache vector search results: {e}")

        return ResponseFormat(data=documents).to_json()
    except Exception as e:
        return ResponseFormat(status=Status.UNKNOWN_ERROR, message=str(e)).to_json()


salesperson_mcp_logger.info("Initializing ADK tool for salesperson...")
find_product_tool = FunctionTool(find_product)
calc_shipping_tool = FunctionTool(calc_shipping)
reserve_stock_tool = FunctionTool(reserve_stock)
generate_context_id_tool = FunctionTool(generate_context_id)
generate_return_url_tool = FunctionTool(generate_return_url)
generate_cancel_url_tool = FunctionTool(generate_cancel_url)
search_product_documents_tool = FunctionTool(search_product_documents)

ADK_TOOLS_FOR_SALESPERSON = {
    find_product_tool.name: find_product_tool,
    calc_shipping_tool.name: calc_shipping_tool,
    reserve_stock_tool.name: reserve_stock_tool,
    generate_context_id_tool.name: generate_context_id_tool,
    generate_return_url_tool.name: generate_return_url_tool,
    generate_cancel_url_tool.name: generate_cancel_url_tool,
    search_product_documents_tool.name: search_product_documents_tool,
}

for adk_tool in ADK_TOOLS_FOR_SALESPERSON.values():
    salesperson_mcp_logger.info(f"ADK tool '{adk_tool.name}' initialized and ready to be exposed via MCP.")