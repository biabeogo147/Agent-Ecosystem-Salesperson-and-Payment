from pymilvus import CollectionSchema, MilvusClient, DataType
from pymilvus.milvus_client import IndexParams

from config import *
from config import RENEW_VS, VS_NAME
from data.vs_connection import get_client_instance


def setup_vector_store():
    """Set up the vector store by initializing the database and collections."""
    if RENEW_VS:
        drop_vs(VS_NAME)
    init_vs(VS_NAME)


def init_vs(db_name: str):
    """Initialize the database and index with LlamaIndex."""
    client = get_client_instance()
    try:
        databases = client.list_databases()
        if db_name not in databases:
            print(f"Initializing database {db_name}...")
            create_vs(db_name)
        else:
            client.use_database(db_name=db_name)
            print(f"Using existing database {db_name}.")
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        raise


def create_vs(db_name: str):
    """database.replica.number (integer): The number of replicas for the specified database.
    database.resource.groups (string): The names of the resource groups associated with the specified database in a comma-separated list.
    database.diskquota.mb (integer): The maximum size of the disk space for the specified database, in megabytes (MB).
    database.max.collections (integer): The maximum number of collections allowed in the specified database.
    database.force.deny.writing (boolean): Whether to force the specified database to deny writing operations.
    database.force.deny.reading (boolean): Whether to force the specified database to deny reading operations."""
    client = get_client_instance()
    client.create_database(
        db_name=db_name,
        properties=None,
    )
    client.use_database(
        db_name=db_name,
    )
    print(f"Database {db_name} created and set as current database.")


def drop_vs(db_name: str):
    """Drop the database and all its collections."""
    client = get_client_instance()
    try:
        if db_name not in client.list_databases():
            print(f"Database {db_name} does not exist.")
            return
        client.use_database(db_name=db_name)
        collections = client.list_collections()
        for collection in collections:
            client.drop_collection(collection_name=collection)
            print(f"Collection {collection} dropped.")
        client.drop_database(db_name=db_name)
        print(f"Database {db_name} dropped.")
    except Exception as e:
        print(f"Failed to drop database: {e}")
        raise


def create_schema() -> CollectionSchema:
    schema = MilvusClient.create_schema(
        auto_id=True,
        enable_dynamic_field=IS_METADATA,
    )
    schema.add_field(
        datatype=DataType.INT64,
        element_type=None,
        field_name="id",
        is_primary=True,
        auto_id=False,
        dim=None,
    )
    schema.add_field(
        field_name=DEFAULT_EMBEDDING_FIELD,
        datatype=DataType.FLOAT_VECTOR,
        dim=EMBED_VECTOR_DIM,
        element_type=None,
        is_primary=False,
        auto_id=False,
    )
    schema.add_field(
        field_name=DEFAULT_TEXT_FIELD,
        datatype=DataType.VARCHAR,
        element_type=None,
        is_primary=False,
        max_length=500,
        auto_id=False,
    )
    return schema


def create_index_params() -> IndexParams:
    client = get_client_instance()
    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="id",
        index_type="AUTOINDEX",
    )
    index_params.add_index(
        index_type="AUTOINDEX",
        index_name="dense_vector_index",
        metric_type=DEFAULT_METRIC_TYPE,
        field_name=DEFAULT_EMBEDDING_FIELD,
    )
    return index_params


def create_collection(collection_name: str):
    schema = create_schema()
    client = get_client_instance()
    index_params = create_index_params()
    client.create_collection(
        collection_name=collection_name,
        index_params=index_params,
        schema=schema,
    )
    print(f"Collection {collection_name} created.")


def drop_collection(collection_name: str):
    client = get_client_instance()
    try:
        if collection_name not in client.list_collections():
            print(f"Collection {collection_name} does not exist.")
            return
        client.drop_collection(collection_name=collection_name)
        print(f"Collection {collection_name} dropped.")
    except Exception as e:
        print(f"Failed to drop collection: {e}")
        raise


def insert_data(collection_name: str, data: list[dict]):
    client = get_client_instance()
    try:
        client.insert(collection_name=collection_name, data=data)
        print(f"Inserted {len(data)} data into collection {collection_name}.")
    except Exception as e:
        print(f"Failed to insert data: {e}")
        raise