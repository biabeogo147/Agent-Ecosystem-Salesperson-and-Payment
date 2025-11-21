import time
from src.config import ELASTIC_INDEX
from src.data.es_connection import ElasticConnection
from src.data.operations.product_ops import find_products_list_by_substring
from src.data.elasic_search.elastic_search_index import create_products_index
from src.data.elasic_search.sync_db_to_es import sync_products_to_elastic


def test_full_pipeline_cleanup():
    es = ElasticConnection().get_client()

    try:
        create_products_index()

        sync_products_to_elastic()

        es.indices.refresh(index=ELASTIC_INDEX)
        time.sleep(1)

        results = find_products_list_by_substring("Mouse")
        assert len(results) > 0, "❌ No results found for 'Mouse'"
        print(f"✅ Found {len(results)} results for 'Mouse'")

    finally:
        if es.indices.exists(index=ELASTIC_INDEX):
            es.indices.delete(index=ELASTIC_INDEX)
            print(f"🧹 Deleted index '{ELASTIC_INDEX}' after test.")