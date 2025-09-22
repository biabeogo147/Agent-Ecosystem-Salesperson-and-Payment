from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH

from config import *

PAYMENT_BASE_URL = f"http://{PAYMENT_AGENT_SERVER_HOST}:{PAYMENT_AGENT_SERVER_PORT}"

payment_remote = RemoteA2aAgent(
    name="payment_agent_remote",
    description="Remote Payment Agent via A2A",
    agent_card=f"{PAYMENT_BASE_URL}{AGENT_CARD_WELL_KNOWN_PATH}",
)