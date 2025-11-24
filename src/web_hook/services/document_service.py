from typing import List

from pymilvus import MilvusException

from src.utils.logger import logger
from src.data.milvus.connection import get_client_instance
from src.web_hook.schemas.document_schemas import DocumentCreate
from src.config import DEFAULT_EMBEDDING_FIELD, DEFAULT_TEXT_FIELD, EMBED_VECTOR_DIM


def generate_mock_embedding(text: str) -> List[float]:
    """Generate a mock embedding vector. Replace with real embedding model in production."""
    import random
    random.seed(hash(text) % (2**32))
    return [random.uniform(-1, 1) for _ in range(EMBED_VECTOR_DIM)]


def insert_document(data: DocumentCreate, collection_name: str = "Document") -> dict:
    """Insert a document into the vector database."""
    client = get_client_instance()

    embedding = generate_mock_embedding(data.text)

    doc_data = {
        DEFAULT_TEXT_FIELD: data.text,
        DEFAULT_EMBEDDING_FIELD: embedding,
        "title": data.title,
        "product_sku": data.product_sku or "",
        "chunk_id": data.chunk_id or 0,
        "merchant_id": data.merchant_id or 0,
    }

    logger.info(f"Document text {data.text[:100]}")
    logger.info(f"Document title {data.title}")
    logger.info(f"Document product_sku {data.product_sku}")
    logger.info(f"Document chunk_id {data.chunk_id}")
    logger.info(f"Document merchant_id {data.merchant_id}")

    try:
        result = client.insert(collection_name=collection_name, data=[doc_data])
        logger.info(f"Document inserted successfully with ID {result}")
        return {
            "id": result.get("ids", [None])[0],
            "text": data.text,
            "title": data.title,
            "product_sku": data.product_sku,
            "chunk_id": data.chunk_id,
            "merchant_id": data.merchant_id,
        }
    except MilvusException as e:
        logger.error(f"Failed to insert document: {e.message}")
        raise RuntimeError(f"Failed to insert document: MilvusException")
    except Exception as e:
        logger.error(f"Failed to insert document: {e}")
        raise RuntimeError(f"Failed to insert document: {e}")