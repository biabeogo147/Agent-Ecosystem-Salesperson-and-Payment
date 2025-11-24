"""Elasticsearch module for search and indexing operations."""

from src.data.elasticsearch.connection import ElasticConnection, es_connection

__all__ = ["ElasticConnection", "es_connection"]
