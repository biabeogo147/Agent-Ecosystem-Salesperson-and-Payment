from src.config import ELASTIC_INDEX
from src.data.es_connection import es_connection
from src.utils.logger import logger


def index_exists() -> bool:
    """Check if the products index exists in Elasticsearch."""
    es = es_connection.get_client()
    return es.indices.exists(index=ELASTIC_INDEX)


def create_products_index():
    """Create the products index in Elasticsearch with proper mapping and analyzers."""
    es = es_connection.get_client()
    
    if es.indices.exists(index=ELASTIC_INDEX):
        logger.info(f"Index '{ELASTIC_INDEX}' already exists.")
        return

    settings = {
        "settings": {
            "analysis": {
                "analyzer": {
                    "text_analyzer": {
                        "tokenizer": "standard",
                        "filter": ["lowercase", "asciifolding"]
                    },
                    "autocomplete_analyzer": {
                        "tokenizer": "edge_ngram_tokenizer",
                        "filter": ["lowercase"]
                    }
                },
                "tokenizer": {
                    "edge_ngram_tokenizer": {
                        "type": "edge_ngram",
                        "min_gram": 2,
                        "max_gram": 15,
                        "token_chars": ["letter", "digit"]
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "sku": {"type": "keyword"},
                "name": {
                    "type": "text",
                    "analyzer": "text_analyzer",
                    "fields": {
                        "autocomplete": {"type": "text", "analyzer": "autocomplete_analyzer"}
                    }
                },
                "price": {"type": "float"},
                "currency": {"type": "keyword"},
                "stock": {"type": "integer"},
                "merchant_id": {"type": "integer"}
            }
        }
    }

    es.indices.create(index=ELASTIC_INDEX, body=settings)
    logger.info(f"Index '{ELASTIC_INDEX}' created successfully.")