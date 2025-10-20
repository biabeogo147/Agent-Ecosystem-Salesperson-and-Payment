from sqlalchemy import text
from config import POSTGRES_DB
from data.db_connection import PostgresConnection
from data.es_connection import ElasticConnection


def test_postgres_connection():
    print("🔍 Testing PostgreSQL connection...")
    try:
        db = PostgresConnection(database=POSTGRES_DB)
        session = db.get_session()
        result = session.execute(text("SELECT version();"))
        print("✅ PostgreSQL connected successfully!")
        print("📦 Version:", result.fetchone()[0])
        session.close()
    except Exception as e:
        print("❌ PostgreSQL connection failed:", e)


def test_elasticsearch_connection():
    print("\n🔍 Testing Elasticsearch connection...")
    try:
        es_client = ElasticConnection().get_client()
        if es_client.ping():
            print("✅ Elasticsearch connected successfully!")
            print("📦 Cluster info:", es_client.info().body)
        else:
            print("❌ Elasticsearch ping failed.")
    except Exception as e:
        print("❌ Elasticsearch connection failed:", e)


def test_milvus_connection():
    from data.vs_connection import get_client_instance
    print("\n🔍 Testing Milvus connection...")
    try:
        milvus_client = get_client_instance()
        version = milvus_client.get_server_version()
        print(f"✅ Milvus is healthy. Server version: {version}")
    except Exception as e:
        print("❌ Milvus connection failed:", e)
