from pymilvus import MilvusClient

from src.data.milvus.milvus_ops import create_collection
from src.data.models.vs_entity import list_vs_entity
from src.utils.logger import get_current_logger

logger = get_current_logger()


def ensure_all_vs_models(client: MilvusClient):
    """
    Ensure that all models declared in vs_entity.list_vs_entity have corresponding Milvus collections.
    """
    if not list_vs_entity:
        logger.warning("⚠️ No models found in list_vs_entity.")
        return

    logger.info(f"🔍 Found {len(list_vs_entity)} vector-store models:")
    for model in list_vs_entity:
        collection_name = model.__name__
        logger.info(f"  → Ensuring collection for model: {collection_name}")
        ensure_collection(client, collection_name)

    logger.info("✅ All vector-store collections ensured successfully.")


def ensure_collection(client: MilvusClient, collection_name: str):
    """
    Check if the collection exists; if not, create it.
    """
    collections = client.list_collections()

    if collection_name not in collections:
        logger.info(f"Collection '{collection_name}' not found. Creating new collection...")
        create_collection(client, collection_name)
    else:
        logger.info(f"Collection '{collection_name}' already exists.")
