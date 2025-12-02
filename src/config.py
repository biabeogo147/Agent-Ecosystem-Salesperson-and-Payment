import os
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = os.environ.get("MODEL_NAME")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE")
IS_LLM_AGENT = os.getenv("IS_LLM_AGENT", "false").lower() == "true"

MCP_SERVER_HOST_PAYMENT = os.getenv("MCP_SERVER_HOST_PAYMENT", "localhost")
MCP_SERVER_PORT_PAYMENT = int(os.getenv("MCP_SERVER_PORT_PAYMENT", "8002"))
MCP_PAYMENT_TOKEN = os.getenv("MCP_PAYMENT_TOKEN", "secret-token")

MCP_SERVER_HOST_SALESPERSON = os.getenv("MCP_SERVER_HOST_SALESPERSON", "localhost")
MCP_SERVER_PORT_SALESPERSON = int(os.getenv("MCP_SERVER_PORT_SALESPERSON", "8001"))
MCP_SALESPERSON_TOKEN = os.getenv("MCP_SALESPERSON_TOKEN", "secret-token")

PAYMENT_AGENT_SERVER_HOST = os.getenv("PAYMENT_AGENT_SERVER_HOST", "localhost")
PAYMENT_AGENT_SERVER_PORT = int(os.getenv("PAYMENT_AGENT_SERVER_PORT", os.getenv("A2A_PORT", "8081")))

PAYGATE_PROVIDER = os.getenv("PAYGATE_PROVIDER", "nganluong")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_DB = os.getenv("POSTGRES_DB", "shop_db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_USER = os.getenv("POSTGRES_USER")

ELASTIC_HOST = os.getenv("ELASTIC_HOST", "localhost")
ELASTIC_PORT = int(os.getenv("ELASTIC_PORT", "9200"))
ELASTIC_INDEX = "products_index"

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost:19530")
MILVUS_USER = os.getenv("MILVUS_USER", "root")
MILVUS_PASSWORD = os.getenv("MILVUS_PASSWORD", "Milvus")
RENEW_VS = os.getenv("RENEW_VS", "false").lower() == "true"
VS_NAME = os.getenv("VS_NAME", "knowledge_base_vs")
IS_METADATA = True
EMBED_VECTOR_DIM = 1024
DEFAULT_TEXT_FIELD = "text"
DEFAULT_METRIC_TYPE = "COSINE"
KNOWLEDGE_BASE_DB = "knowledge_base"
DEFAULT_EMBEDDING_FIELD = "embedding"

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8082"))

CALLBACK_SERVICE_HOST = os.getenv("CALLBACK_SERVICE_HOST", "0.0.0.0")
CALLBACK_SERVICE_PORT = int(os.getenv("CALLBACK_SERVICE_PORT", "8083"))
CALLBACK_SERVICE_URL = os.getenv("CALLBACK_SERVICE_URL", "http://localhost:8083")
CHECKOUT_URL=os.getenv("CHECKOUT_URL", "http://localhost:8083/checkout")
QR_URL=os.getenv("QR_URL", "http://localhost:8083/qr")

WS_SERVER_HOST = os.getenv("WS_SERVER_HOST", "0.0.0.0")
WS_SERVER_PORT = int(os.getenv("WS_SERVER_PORT", "8084"))

CHAT_UI_HOST = os.getenv("CHAT_UI_HOST", "0.0.0.0")
CHAT_UI_PORT = int(os.getenv("CHAT_UI_PORT", "8085"))
ADK_AGENT_URL = os.getenv("ADK_AGENT_URL", "http://localhost:8000")

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours default