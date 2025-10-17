import os
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = os.environ.get("MODEL_NAME")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE")
IS_LLM_AGENT = os.getenv("IS_LLM_AGENT", "false").lower() == "true"

MCP_SERVER_HOST_PAYMENT = os.getenv("MCP_SERVER_HOST_PAYMENT", "localhost")
MCP_SERVER_PORT_PAYMENT = int(os.getenv("MCP_SERVER_PORT_PAYMENT", "8000"))
MCP_PAYMENT_TOKEN = os.getenv("MCP_PAYMENT_TOKEN", "secret-token")
RETURN_URL=os.getenv("RETURN_URL", "http://localhost:3000/return")
CANCEL_URL=os.getenv("CANCEL_URL", "http://localhost:3000/cancel")
CHECKOUT_URL=os.getenv("CHECKOUT_URL", "http://localhost:3000/checkout")
QR_URL=os.getenv("QR_URL", "http://localhost:3000/qr")

MCP_SERVER_HOST_SALESPERSON = os.getenv("MCP_SERVER_HOST_SALESPERSON", "localhost")
MCP_SERVER_PORT_SALESPERSON = int(os.getenv("MCP_SERVER_PORT_SALESPERSON", "8001"))
MCP_SALESPERSON_TOKEN = os.getenv("MCP_SALESPERSON_TOKEN", "secret-token")

PAYMENT_AGENT_SERVER_HOST = os.getenv("PAYMENT_AGENT_SERVER_HOST", "localhost")
PAYMENT_AGENT_SERVER_PORT = int(os.getenv("PAYMENT_AGENT_SERVER_PORT", os.getenv("A2A_PORT", "8081")))

PAYGATE_PROVIDER = os.getenv("PAYGATE_PROVIDER", "nganluong")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_DB = os.getenv("POSTGRES_DB", "shop_db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
PGADMIN_DEFAULT_EMAIL = os.getenv("PGADMIN_DEFAULT_EMAIL")
PGADMIN_DEFAULT_PASSWORD = os.getenv("PGADMIN_DEFAULT_PASSWORD")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_USER = os.getenv("POSTGRES_USER")

ELASTIC_HOST = os.getenv("ELASTIC_HOST", "localhost")
ELASTIC_PORT = int(os.getenv("ELASTIC_PORT", "9200"))
ELASTIC_USER = os.getenv("ELASTIC_USER", "es_salesperson")
ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD", "123456")
ELASTIC_INDEX = "products_index"