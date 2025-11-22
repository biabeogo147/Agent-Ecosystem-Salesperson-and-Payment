from src.web_hook.services.product_service import (
    create_product,
    update_product,
    get_product,
    get_all_products,
    delete_product,
)
from src.web_hook.services.document_service import (
    insert_document,
    generate_mock_embedding,
)

__all__ = [
    "create_product",
    "update_product",
    "get_product",
    "get_all_products",
    "delete_product",
    "insert_document",
    "generate_mock_embedding",
]