from data.milvus.milvus_ops import create_collection
from data.models.vs_entity import list_vs_entity
from data.vs_connection import get_client_instance


def ensure_all_vs_models():
    """
    Ensure that all models declared in vs_entity.list_vs_entity have corresponding Milvus collections.
    """
    if not list_vs_entity:
        print("⚠️ No models found in list_vs_entity.")
        return

    print(f"🔍 Found {len(list_vs_entity)} vector-store models:")
    for model in list_vs_entity:
        collection_name = model.__name__
        print(f"  → Ensuring collection for model: {collection_name}")
        ensure_collection(collection_name)

    print("✅ All vector-store collections ensured successfully.")


def ensure_collection(collection_name: str):
    """
    Check if the collection exists; if not, create it.
    """
    client = get_client_instance()
    collections = client.list_collections()

    if collection_name not in collections:
        print(f"Collection '{collection_name}' not found. Creating new collection...")
        create_collection(collection_name)
    else:
        print(f"Collection '{collection_name}' already exists.")
