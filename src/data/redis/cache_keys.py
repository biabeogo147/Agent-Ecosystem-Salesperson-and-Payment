class TTL:
    """Time-to-Live constants for different cache types."""
    PRODUCT = 300           # 5 minutes - product details
    PRODUCT_STOCK = 30      # 30 seconds - stock levels (changes frequently)
    SEARCH = 120            # 2 minutes - search results
    PRODUCT_LIST = 180      # 3 minutes - product lists
    VECTOR_SEARCH = 600     # 10 minutes - vector search (embeddings rarely change)


class CacheKeys:
    """Cache key generators for all Redis keys."""

    # Product-related keys
    @staticmethod
    def product_by_sku(sku: str) -> str:
        """Cache key for product by SKU."""
        return f"product:sku:{sku}"

    @staticmethod
    def product_by_merchant_and_sku(merchant_id: int, sku: str) -> str:
        """Cache key for product filtered by merchant and SKU."""
        return f"product:merchant:{merchant_id}:sku:{sku}"

    @staticmethod
    def products_by_merchant(merchant_id: int) -> str:
        """Cache key for all products by merchant."""
        return f"products:merchant:{merchant_id}"

    @staticmethod
    def all_products() -> str:
        """Cache key for all products."""
        return "products:all"

    # Search-related keys
    @staticmethod
    def search_products(query: str, min_price: float = None, max_price: float = None,
                       merchant_id: int = None, limit: int = 20) -> str:
        """Cache key for product search results."""
        filters = f"min:{min_price}_max:{max_price}_merchant:{merchant_id}_limit:{limit}"
        return f"search:products:{query}:{filters}"

    @staticmethod
    def vector_search(query: str, product_sku: str = None, limit: int = 5) -> str:
        """Cache key for vector search results."""
        return f"vector:search:{query}:{product_sku}:{limit}"

    # Sync tracking keys
    @staticmethod
    def elasticsearch_synced_skus() -> str:
        """Redis Set key for tracking SKUs synced to Elasticsearch."""
        return "elasticsearch:synced_skus"


class CachePatterns:
    """Cache key patterns for bulk operations (invalidation, clearing)."""

    @staticmethod
    def products_by_merchant_pattern(merchant_id: int) -> str:
        """Pattern to match all product keys for a specific merchant."""
        return f"products:merchant:{merchant_id}*"

    @staticmethod
    def all_products_pattern() -> str:
        """Pattern to match all product list keys."""
        return "products:all*"

    @staticmethod
    def search_products_pattern() -> str:
        """Pattern to match all product search keys."""
        return "search:products:*"

    @staticmethod
    def all_pattern() -> str:
        """Pattern to match all cache keys (use with caution!)."""
        return "*"
