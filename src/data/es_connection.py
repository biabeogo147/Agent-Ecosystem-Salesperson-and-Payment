import config
from elasticsearch import Elasticsearch

class ElasticConnection:
    def __init__(self):
        self.es = Elasticsearch(
            hosts=[{"host": config.ELASTIC_HOST, "port": config.ELASTIC_PORT, "scheme": "http"}],
            basic_auth=(config.ELASTIC_USER, config.ELASTIC_PASSWORD),
            verify_certs=False
        )

    def get_client(self):
        return self.es
