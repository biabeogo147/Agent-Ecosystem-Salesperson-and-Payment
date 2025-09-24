from google.adk.a2a.utils.agent_to_a2a import to_a2a

from my_a2a import build_payment_agent_card
from my_agent.payment_agent.agent import root_agent
from config import PAYMENT_AGENT_SERVER_HOST, PAYMENT_AGENT_SERVER_PORT

_CARD_BASE_URL = f"http://{PAYMENT_AGENT_SERVER_HOST}:{PAYMENT_AGENT_SERVER_PORT}/"
_PAYMENT_AGENT_CARD = build_payment_agent_card(_CARD_BASE_URL)

a2a_app = to_a2a(
    root_agent,
    host=PAYMENT_AGENT_SERVER_HOST,
    port=PAYMENT_AGENT_SERVER_PORT,
    agent_card=_PAYMENT_AGENT_CARD,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "my_agent.payment_agent.a2a_app:a2a_app",
        host="0.0.0.0",
        port=PAYMENT_AGENT_SERVER_PORT,
    )