import httpx
import time
from typing import Optional

from a2a.types import AgentCard
from google.adk.agents.remote_a2a_agent import (
    RemoteA2aAgent,
    AGENT_CARD_WELL_KNOWN_PATH,
)

from config import *

PAYMENT_BASE_URL = f"http://{PAYMENT_AGENT_SERVER_HOST}:{PAYMENT_AGENT_SERVER_PORT}"
AGENT_CARD_URL = f"{PAYMENT_BASE_URL}{AGENT_CARD_WELL_KNOWN_PATH}"
_AGENT_CARD_CACHE: Optional[AgentCard] = None
_AGENT_CARD_TTL = 60  # seconds
_AGENT_CARD_FETCHED_AT = 0.0


def get_remote_payment_agent() -> RemoteA2aAgent:
    return RemoteA2aAgent(
        name="payment_agent_remote",
        description="Remote Payment Agent via A2A",
        agent_card=AGENT_CARD_URL,
    )


def _get_payment_agent_card() -> AgentCard:
    global _AGENT_CARD_CACHE, _AGENT_CARD_FETCHED_AT, _AGENT_CARD_TTL

    now = time.time()
    if _AGENT_CARD_CACHE and (now - _AGENT_CARD_FETCHED_AT) < _AGENT_CARD_TTL:
        return _AGENT_CARD_CACHE
    with httpx.Client(timeout=10) as client:
        resp = client.get(AGENT_CARD_URL)
        resp.raise_for_status()
        _AGENT_CARD_CACHE = AgentCard.model_validate(resp.json())
        _AGENT_CARD_FETCHED_AT = now
        return _AGENT_CARD_CACHE


def get_payment_agent_card() -> AgentCard:
    """Expose the cached :class:`AgentCard` for non-agent helpers."""

    return _get_payment_agent_card()


__all__ = ["get_remote_payment_agent", "get_payment_agent_card"]
