from data.db_connection import PostgresConnection
from data.es_connection import ElasticConnection
from data.models.product import Product
from config import ELASTIC_INDEX

def sync_products_to_elastic():
    pg = PostgresConnection(database="product_db")
    session = pg.get_session()
    es = ElasticConnection().get_client()

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
    print(f"✅ Indexed {len(actions)} products into Elasticsearch.")
    session.close()
