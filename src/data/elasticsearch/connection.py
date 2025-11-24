from elasticsearch import Elasticsearch
from src.config import ELASTIC_HOST, ELASTIC_PORT


class ElasticConnection:
    """
    Elasticsearch connection manager.

    Provides connection to Elasticsearch cluster for search and indexing operations.
    """

    def __init__(self):
        """Initialize Elasticsearch connection."""
        self.es = Elasticsearch(
            hosts=[{"host": ELASTIC_HOST, "port": ELASTIC_PORT, "scheme": "http"}],
            verify_certs=False
        )

    def get_client(self):
        """
        Get Elasticsearch client instance.

        Returns:
            Elasticsearch client object
        """
        return self.es


es_connection = ElasticConnection()
