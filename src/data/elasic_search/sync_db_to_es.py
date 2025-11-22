from src.data.db_connection import db_connection
from src.data.es_connection import es_connection
from src.data.models.db_entity.product import Product
from src.config import ELASTIC_INDEX
from src.utils.logger import logger

def sync_products_to_elastic():
    pg = db_connection
    session = pg.get_session()
    es = es_connection

    products = session.query(Product).all()
    actions = [
        {
            "_op_type": "index",
            "_index": ELASTIC_INDEX,
            "_id": p.sku,
            "_source": p.to_dict()
        }
        for p in products
    ]

    from elasticsearch.helpers import bulk
    bulk(es, actions)
    logger.info(f"✅ Indexed {len(actions)} products into Elasticsearch.")
    session.close()
