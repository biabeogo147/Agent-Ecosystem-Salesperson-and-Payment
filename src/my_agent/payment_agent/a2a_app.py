from google.adk.a2a.utils.agent_to_a2a import to_a2a

from my_agent.payment_agent.agent import root_agent
from my_a2a import build_payment_agent_card
from config import (
    A2A_PORT,
    PAYMENT_AGENT_SERVER_HOST,
    PAYMENT_AGENT_SERVER_PORT,
)

_RPC_HOST = PAYMENT_AGENT_SERVER_HOST or "localhost"
_RPC_PORT = PAYMENT_AGENT_SERVER_PORT or A2A_PORT
_CARD_BASE_URL = f"http://{_RPC_HOST}:{_RPC_PORT}/"

# Turn agent into an A2A app using the handcrafted agent card.
_PAYMENT_AGENT_CARD = build_payment_agent_card(_CARD_BASE_URL)
a2a_app = to_a2a(
    root_agent,
    host=_RPC_HOST,
    port=_RPC_PORT,
    agent_card=_PAYMENT_AGENT_CARD,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "my_agent.payment_agent.a2a_app:a2a_app",
        host="0.0.0.0",
        port=_RPC_PORT,
    )