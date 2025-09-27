from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

from a2a.types import AgentCard

from my_agent.payment_agent.payment_a2a import build_payment_agent_card
from my_agent.salesperson_agent.salesperson_a2a import remote_agent


@dataclass
class _DummyResponse:
    payload: Any

    def json(self) -> Any:
        return self.payload

    def raise_for_status(self) -> None:
        return None


class _DummyClient:
    def __init__(self, response: _DummyResponse) -> None:
        self._response = response
        self.calls = 0

    def __enter__(self) -> "_DummyClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, url: str) -> _DummyResponse:
        self.calls += 1
        assert url == remote_agent.AGENT_CARD_URL
        return self._response


def test_get_payment_agent_card() -> None:
    card_payload = build_payment_agent_card("http://payment").model_dump(mode="json")
    dummy_client = _DummyClient(_DummyResponse(card_payload))

    original_cache = remote_agent._AGENT_CARD_CACHE
    original_fetch_time = remote_agent._AGENT_CARD_FETCHED_AT
    try:
        remote_agent._AGENT_CARD_CACHE = None
        remote_agent._AGENT_CARD_FETCHED_AT = 0.0

        with patch(
            "my_agent.salesperson_agent.salesperson_a2a.remote_agent.httpx.Client",
            return_value=dummy_client,
        ):
            card_first = remote_agent._get_payment_agent_card()
            card_second = remote_agent._get_payment_agent_card()

        assert isinstance(card_first, AgentCard)
        assert card_second is card_first
        assert dummy_client.calls == 1
    finally:
        remote_agent._AGENT_CARD_CACHE = original_cache
        remote_agent._AGENT_CARD_FETCHED_AT = original_fetch_time
