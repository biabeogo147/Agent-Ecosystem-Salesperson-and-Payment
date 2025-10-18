import config
from elasticsearch import Elasticsearch

class ElasticConnection:
    def __init__(self):
        self.es = Elasticsearch(
            hosts=[{"host": config.ELASTIC_HOST, "port": config.ELASTIC_PORT, "scheme": "http"}],
            verify_certs=False
        )

    def get_client(self):
        return self.es

es_connection = ElasticConnection()