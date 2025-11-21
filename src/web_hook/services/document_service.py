from typing import Optional, List
import hashlib

from src.data.vs_connection import get_client_instance
from src.config import DEFAULT_EMBEDDING_FIELD, DEFAULT_TEXT_FIELD, EMBED_VECTOR_DIM
from src.web_hook.schemas.document_schemas import DocumentCreate


def generate_document_id(text: str, product_sku: Optional[str], chunk_id: Optional[int]) -> int:
    """Generate a unique document ID based on content hash."""
    content = f"{text}:{product_sku or ''}:{chunk_id or 0}"
    hash_bytes = hashlib.md5(content.encode()).digest()
    return int.from_bytes(hash_bytes[:8], byteorder='big') & 0x7FFFFFFFFFFFFFFF


def generate_mock_embedding(text: str) -> List[float]:
    """Generate a mock embedding vector. Replace with real embedding model in production."""
    import random
    random.seed(hash(text) % (2**32))
    return [random.uniform(-1, 1) for _ in range(EMBED_VECTOR_DIM)]


def insert_document(data: DocumentCreate, collection_name: str = "Document") -> dict:
    """Insert a document into the vector database."""
    client = get_client_instance()

    doc_id = generate_document_id(data.text, data.product_sku, data.chunk_id)
    embedding = generate_mock_embedding(data.text)

    doc_data = {
        "id": doc_id,
        DEFAULT_TEXT_FIELD: data.text,
        DEFAULT_EMBEDDING_FIELD: embedding,
        "title": data.title,
        "product_sku": data.product_sku or "",
        "chunk_id": data.chunk_id or 0,
    }

    try:
        client.insert(collection_name=collection_name, data=[doc_data])
        return {
            "id": doc_id,
            "text": data.text,
            "title": data.title,
            "product_sku": data.product_sku,
            "chunk_id": data.chunk_id,
            "message": f"Document inserted successfully with ID {doc_id}"
        }
    except Exception as e:
        raise RuntimeError(f"Failed to insert document: {e}")