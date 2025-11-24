from elasticsearch import Elasticsearch
from src.config import ELASTIC_HOST, ELASTIC_PORT


class ElasticConnection:
    """
    Elasticsearch connection manager.

    Provides connection to Elasticsearch cluster for search and indexing operations.
    """

    def __init__(self):
        """Initialize Elasticsearch connection with optimized pooling and retry settings."""
        self.es = Elasticsearch(
            hosts=[{"host": ELASTIC_HOST, "port": ELASTIC_PORT, "scheme": "http"}],
            verify_certs=False,
            max_retries=3,  # Retry failed requests up to 3 times
            retry_on_timeout=True,  # Retry if request times out
            timeout=30,  # Request timeout in seconds
            maxsize=50,  # Connection pool size for concurrent requests
        )

    def get_client(self):
        """
        Get Elasticsearch client instance.

        Returns:
            Elasticsearch client object
        """
        return self.es


es_connection = ElasticConnection()
