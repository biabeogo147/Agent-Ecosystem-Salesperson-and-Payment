from src.config import ELASTIC_INDEX
from src.data.es_connection import es_connection
from src.utils.logger import logger


def create_products_index():
    es = es_connection
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
                "stock": {"type": "integer"}
            }
        }
    }

    es.indices.create(index=ELASTIC_INDEX, body=settings)
    logger.info(f"Index '{ELASTIC_INDEX}' created successfully.")