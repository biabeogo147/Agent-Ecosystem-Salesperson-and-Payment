from __future__ import annotations

import asyncio

from google.adk.tools import FunctionTool
from passlib.context import CryptContext
from sqlalchemy import select, or_

from . import salesperson_mcp_logger

from src.config import JWT_EXPIRE_MINUTES
from src.utils.client import embed
from src.utils.response_format import ResponseFormat
from src.utils.status import Status
from src.utils.jwt_utils import create_access_token
from src.data.models.db_entity.user import User
from src.data.postgres.connection import db_connection

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
from src.utils.app_string import *
from src.data.redis.cache_ops import get_cached_value, set_cached_value
from src.data.redis.cache_keys import CacheKeys, TTL
from src.data.elasticsearch.search_ops import find_products_by_text
from src.data.postgres.product_ops import find_product_by_sku, update_product_stock
from src.data.milvus.connection import get_client_instance


async def _cache_documents(cache_key: str, documents: list):
    """Background task to cache vector search results."""
    try:
        await set_cached_value(cache_key, documents, ttl=TTL.VECTOR_SEARCH)
        salesperson_mcp_logger.debug(f"Cached vector search results: {cache_key}")
    except Exception as e:
        salesperson_mcp_logger.warning(f"Failed to cache vector search results: {e}")


async def find_product(query: str) -> str:
    """
    Find product by SKU or substring of name.
    """
    salesperson_mcp_logger.info(f"Find product: {query}")
    query = query.lower()
    results = await find_products_by_text(query)
    return ResponseFormat(data=results).to_json()


async def calc_shipping(weight: float, distance: float) -> str:
    """
    Calculate shipping cost based on weight (kg) and distance (km).
    """
    salesperson_mcp_logger.info(f"Calculate shipping cost: weight={weight}, distance={distance}")
    base_cost = 5.0         # USD
    weight_factor = 1.0     # Kg
    distance_factor = 0.5   # Km

    cost = base_cost + (weight * weight_factor) + (distance * distance_factor)
    return ResponseFormat(data=round(cost, 2)).to_json()


async def reserve_stock(sku: str, quantity: int) -> str:
    """
    Reserve stock for a given SKU and quantity.
    """
    salesperson_mcp_logger.info(f"Reserve stock: sku={sku}, quantity={quantity}")
    product = await find_product_by_sku(sku, use_cache=False)

    if not product:
        return ResponseFormat(status=Status.PRODUCT_NOT_FOUND, data=False, message=PRODUCT_NOT_FOUND).to_json()

    if product.stock < quantity:
        return ResponseFormat(status=Status.QUANTITY_EXCEEDED, data=False, message=QUANTITY_EXCEEDED).to_json()

    result = await update_product_stock(sku, product.stock - quantity)

    return ResponseFormat(data=result).to_json()


async def search_product_documents(query: str, product_sku: str | None = None, limit: int = 5) -> str:
    """
    Search product documents in vector database.
    Args:
        query: Search query text
        product_sku: Optional product SKU to filter results
        limit: Maximum number of results (default 5)
    Returns: List of matching documents
    """
    salesperson_mcp_logger.info(f"Search product documents: query={query}, product_sku={product_sku}, limit={limit}")
    cache_key = CacheKeys.vector_search(query, product_sku, limit)

    try:
        cached = await get_cached_value(cache_key)
        if cached:
            salesperson_mcp_logger.debug(f"Cache HIT: {cache_key}")
            return ResponseFormat(data=cached).to_json()
    except Exception as e:
        salesperson_mcp_logger.warning(f"Cache read failed for {cache_key}, using Milvus: {e}")

    salesperson_mcp_logger.debug(f"Cache MISS: {cache_key}")

    try:
        client = await asyncio.to_thread(get_client_instance)

        query_embedding = await embed(query)

        search_params = {
            "collection_name": "Document",
            "data": [query_embedding],
            "anns_field": "embedding",
            "limit": limit,
            "output_fields": ["id", "text", "title", "product_sku", "chunk_id"],
        }

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

        asyncio.create_task(_cache_documents(cache_key, documents))

        return ResponseFormat(data=documents).to_json()
    except Exception as e:
        return ResponseFormat(status=Status.UNKNOWN_ERROR, message=str(e)).to_json()


async def get_current_user_id(context_id: str) -> str:
    """
    Get the current authenticated user ID for the given context.
    This is called by payment agent to retrieve user_id when creating orders.

    Args:
        context_id: The payment context identifier

    Returns:
        JSON with user_id

    TODO: Implement actual user session lookup based on context_id
    Currently returns a placeholder value.
    """
    salesperson_mcp_logger.info(f"Get current user ID for context: {context_id}")

    # TODO: Implement actual logic to get user_id from session/context
    # This should:
    # 1. Look up the session associated with context_id
    # 2. Extract the authenticated user_id from session
    # 3. Return the user_id

    # Placeholder: Return a mock user_id
    # In production, this should fetch from Redis session or similar
    user_id = 1  # Default user for testing

    salesperson_mcp_logger.debug(f"Retrieved user_id={user_id} for context={context_id}")
    return ResponseFormat(data={"user_id": user_id}).to_json()


async def authenticate_user(username: str, password: str) -> str:
    """
    Authenticate user with username/email and password.
    Returns JWT token and user info if successful.

    Args:
        username: Username or email
        password: User password

    Returns:
        JSON with access_token, token_type, user_id, username, expires_in
        or error status if authentication fails
    """
    salesperson_mcp_logger.info(f"Authenticate user: {username}")
    session = db_connection.get_session()
    try:
        result = await session.execute(
            select(User).where(or_(User.username == username, User.email == username))
        )
        user = result.scalar_one_or_none()

        if not user:
            salesperson_mcp_logger.warning(f"Login failed: user not found - {username}")
            return ResponseFormat(
                status=Status.FAILURE,
                message="Invalid username or password"
            ).to_json()

        if not pwd_context.verify(password, user.hashed_password):
            salesperson_mcp_logger.warning(f"Login failed: invalid password - {username}")
            return ResponseFormat(
                status=Status.FAILURE,
                message="Invalid username or password"
            ).to_json()

        access_token = create_access_token(user_id=user.id, username=user.username)

        salesperson_mcp_logger.info(f"Login successful: user_id={user.id}, username={user.username}")

        return ResponseFormat(data={
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username,
            "expires_in": JWT_EXPIRE_MINUTES * 60
        }).to_json()
    except Exception as e:
        salesperson_mcp_logger.exception(f"Authentication error: {e}")
        return ResponseFormat(status=Status.UNKNOWN_ERROR, message=str(e)).to_json()
    finally:
        await session.close()


salesperson_mcp_logger.info("Initializing ADK tool for salesperson...")
find_product_tool = FunctionTool(find_product)
calc_shipping_tool = FunctionTool(calc_shipping)
reserve_stock_tool = FunctionTool(reserve_stock)
search_product_documents_tool = FunctionTool(search_product_documents)
get_current_user_id_tool = FunctionTool(get_current_user_id)
authenticate_user_tool = FunctionTool(authenticate_user)

ADK_TOOLS_FOR_SALESPERSON = {
    find_product_tool.name: find_product_tool,
    calc_shipping_tool.name: calc_shipping_tool,
    reserve_stock_tool.name: reserve_stock_tool,
    search_product_documents_tool.name: search_product_documents_tool,
    get_current_user_id_tool.name: get_current_user_id_tool,
    authenticate_user_tool.name: authenticate_user_tool,
}

for adk_tool in ADK_TOOLS_FOR_SALESPERSON.values():
    salesperson_mcp_logger.info(f"ADK tool '{adk_tool.name}' initialized and ready to be exposed via MCP.")