from pymilvus import MilvusClient
from src.config import MILVUS_HOST, MILVUS_USER, MILVUS_PASSWORD

_client = None


def get_client_instance() -> MilvusClient:
    """
    Get the Milvus client instance (singleton pattern).

    Returns:
        MilvusClient instance
    """
    from src.data.milvus.ensure_all_vs_models import ensure_all_vs_models

    global _client
    if _client is None:
        _client = MilvusClient(
            uri=MILVUS_HOST,
            token=f"{MILVUS_USER}:{MILVUS_PASSWORD}",
        )
        ensure_all_vs_models(_client)
    return _client


# For backward compatibility
def get_milvus_client() -> MilvusClient:
    """
    Alias for get_client_instance().

    Returns:
        MilvusClient instance
    """
    return get_client_instance()
