from elasticsearch import AsyncElasticsearch
from src.config import ELASTIC_HOST, ELASTIC_PORT
from src.utils.logger import get_current_logger


class ElasticConnection:
    """
    Elasticsearch async connection manager.

    Provides async connection to Elasticsearch cluster for search and indexing operations.
    """

    def __init__(self):
        """Initialize Elasticsearch async connection with optimized pooling and retry settings."""
        logger = get_current_logger()
        self.es = AsyncElasticsearch(
            hosts=[{"host": ELASTIC_HOST, "port": ELASTIC_PORT, "scheme": "http"}],
            verify_certs=False,
            max_retries=3,  # Retry failed requests up to 3 times
            retry_on_timeout=True,  # Retry if request times out
            request_timeout=30,  # Request timeout in seconds
            maxsize=50,  # Connection pool size for concurrent requests
        )
        logger.info(f"✅ Elasticsearch async client initialized: {ELASTIC_HOST}:{ELASTIC_PORT}")

    def get_client(self):
        """
        Get Elasticsearch async client instance.

        Returns:
            AsyncElasticsearch client object
        """
        return self.es

    async def close(self):
        """Close Elasticsearch connection and cleanup resources."""
        logger = get_current_logger()
        await self.es.close()
        logger.info("✅ Elasticsearch connection closed")


es_connection = ElasticConnection()
