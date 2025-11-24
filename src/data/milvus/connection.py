import threading
from pymilvus import MilvusClient
from src.config import MILVUS_HOST, MILVUS_USER, MILVUS_PASSWORD

_client = None
_lock = threading.Lock()


def get_client_instance() -> MilvusClient:
    """
    Get the Milvus client instance with thread-safe initialization (singleton pattern).

    Uses double-checked locking to ensure only one client is created even
    when called concurrently from multiple threads.

    Returns:
        MilvusClient instance
    """
    from src.data.milvus.ensure_all_vs_models import ensure_all_vs_models

    global _client

    # Double-checked locking pattern for thread safety
    if _client is None:
        with _lock:
            # Check again after acquiring lock
            if _client is None:
                _client = MilvusClient(
                    uri=MILVUS_HOST,
                    token=f"{MILVUS_USER}:{MILVUS_PASSWORD}",
                )
                # Only run ensure_all_vs_models once during initialization
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
