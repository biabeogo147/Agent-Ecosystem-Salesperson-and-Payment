import os
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = os.environ.get("MODEL_NAME")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE")

MCP_SERVER_HOST_PAYMENT = os.getenv("MCP_SERVER_HOST_PAYMENT", "localhost")
MCP_SERVER_PORT_PAYMENT = int(os.getenv("MCP_SERVER_PORT_PAYMENT", "8000"))
RETURN_URL=os.getenv("RETURN_URL", "http://localhost:3000/return")
CANCEL_URL=os.getenv("CANCEL_URL", "http://localhost:3000/cancel")
CHECKOUT_URL=os.getenv("CHECKOUT_URL", "http://localhost:3000/checkout")
QR_URL=os.getenv("QR_URL", "http://localhost:3000/qr")

MCP_SERVER_HOST_SALESPERSON = os.getenv("MCP_SERVER_HOST_SALESPERSON", "localhost")
MCP_SERVER_PORT_SALESPERSON = int(os.getenv("MCP_SERVER_PORT_SALESPERSON", "8001"))

PAYMENT_AGENT_SERVER_HOST = os.getenv("PAYMENT_AGENT_SERVER_HOST", "localhost")
PAYMENT_AGENT_SERVER_PORT = int(os.getenv("PAYMENT_AGENT_SERVER_PORT", os.getenv("A2A_PORT", "8081")))