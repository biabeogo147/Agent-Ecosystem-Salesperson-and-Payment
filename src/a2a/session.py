"""Utilities to orchestrate a shopping session between customer and merchant agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .protocol import A2AEndpoint, A2AMessage, A2AProtocol
from merchant_agent.rule_based import RuleBasedMerchantAgent
from shopping_agent.rule_based import RuleBasedShoppingAgent


@dataclass
class ShoppingA2ASession:
    """High-level helper that wires a customer and merchant through the A2A protocol."""

    customer: RuleBasedShoppingAgent
    merchant: RuleBasedMerchantAgent
    protocol: A2AProtocol = field(default_factory=A2AProtocol)

    def __post_init__(self) -> None:
        self.protocol.register(A2AEndpoint(self.customer.name, self.customer.handle_message))
        self.protocol.register(A2AEndpoint(self.merchant.name, self.merchant.handle_message))

    async def start(self) -> Sequence[A2AMessage]:
        """Kick off the shopping workflow and return the full transcript."""

        initial_message = self.customer.build_initial_request(self.merchant.name)
        await self.protocol.send(initial_message)
        return self.protocol.history

    @property
    def history(self) -> Sequence[A2AMessage]:
        """Expose the protocol history for convenience."""

        return self.protocol.history
