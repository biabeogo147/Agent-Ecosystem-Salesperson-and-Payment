from pymilvus import MilvusClient

from config import *

_client = None


def get_client_instance() -> MilvusClient:
    """Get the Milvus client instance."""
    global _client
    if _client is None:
        _client = MilvusClient(
            uri=MILVUS_HOST,
            token=f"{MILVUS_USER}:{MILVUS_PASSWORD}",
        )
    return _client