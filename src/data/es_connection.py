from elasticsearch import Elasticsearch
from src.config import ELASTIC_HOST, ELASTIC_PORT

class ElasticConnection:
    def __init__(self):
        self.es = Elasticsearch(
            hosts=[{"host": ELASTIC_HOST, "port": ELASTIC_PORT, "scheme": "http"}],
            verify_certs=False
        )

    def get_client(self):
        return self.es

es_connection = ElasticConnection()