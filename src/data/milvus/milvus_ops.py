from pymilvus import CollectionSchema, MilvusClient, DataType
from pymilvus.milvus_client import IndexParams
from pymilvus import CollectionSchema, MilvusClient, DataType
from pymilvus.milvus_client import IndexParams

from src.config import *
from src.config import RENEW_VS, VS_NAME

from src.utils.logger import logger

from src.data.vs_connection import get_client_instance


def setup_vector_store(client: MilvusClient):
    """Set up the vector store by initializing the database and collections."""
    if RENEW_VS:
        drop_vs(client, VS_NAME)
    init_vs(client, VS_NAME)


def init_vs(client: MilvusClient, db_name: str):
    """Initialize the database and index with LlamaIndex."""
    try:
        databases = client.list_databases()
        if db_name not in databases:
            logger.info(f"Initializing database {db_name}...")
            create_vs(client, db_name)
        else:
            client.use_database(db_name=db_name)
            logger.info(f"Using existing database {db_name}.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def create_vs(client: MilvusClient, db_name: str):
    """database.replica.number (integer): The number of replicas for the specified database.
    database.resource.groups (string): The names of the resource groups associated with the specified database in a comma-separated list.
    database.diskquota.mb (integer): The maximum size of the disk space for the specified database, in megabytes (MB).
    database.max.collections (integer): The maximum number of collections allowed in the specified database.
    database.force.deny.writing (boolean): Whether to force the specified database to deny writing operations.
    database.force.deny.reading (boolean): Whether to force the specified database to deny reading operations."""
    client.create_database(
        db_name=db_name,
        properties=None,
    )
    client.use_database(
        db_name=db_name,
    )
    logger.info(f"Database {db_name} created and set as current database.")


def drop_vs(client: MilvusClient, db_name: str):
    """Drop the database and all its collections."""
    try:
        if db_name not in client.list_databases():
            logger.warning(f"Database {db_name} does not exist.")
            return
        client.use_database(db_name=db_name)
        collections = client.list_collections()
        for collection in collections:
            client.drop_collection(collection_name=collection)
            logger.info(f"Collection {collection} dropped.")
        client.drop_database(db_name=db_name)
        logger.info(f"Database {db_name} dropped.")
    except Exception as e:
        logger.error(f"Failed to drop database: {e}")
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


def create_index_params(client: MilvusClient) -> IndexParams:
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


def create_collection(client: MilvusClient, collection_name: str):
    schema = create_schema()
    index_params = create_index_params(client)
    client.create_collection(
        collection_name=collection_name,
        index_params=index_params,
        schema=schema,
    )
    logger.info(f"Collection {collection_name} created.")


def drop_collection(client: MilvusClient, collection_name: str):
    try:
        if collection_name not in client.list_collections():
            logger.warning(f"Collection {collection_name} does not exist.")
            return
        client.drop_collection(collection_name=collection_name)
        logger.info(f"Collection {collection_name} dropped.")
    except Exception as e:
        logger.error(f"Failed to drop collection: {e}")
        raise


def insert_data(client: MilvusClient, collection_name: str, data: list[dict]):
    try:
        client.insert(collection_name=collection_name, data=data)
        logger.info(f"Inserted {len(data)} data into collection {collection_name}.")
    except Exception as e:
        logger.error(f"Failed to insert data: {e}")
        raise