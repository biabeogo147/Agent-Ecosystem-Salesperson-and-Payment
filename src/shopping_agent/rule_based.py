"""Rule-based shopping agent for protocol simulations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from utils.status import Status


@dataclass
class RuleBasedShoppingAgent:
    """Deterministic customer agent that drives the shopping workflow."""

    desired_sku: str
    quantity: int
    shipping_weight: float
    shipping_distance: float
    budget: float | None = None
    name: str = "shopping_agent"

    _state: str = field(init=False, default="idle")
    _product: Mapping[str, Any] | None = field(init=False, default=None)
    _shipping_cost: float | None = field(init=False, default=None)
    _last_error: Mapping[str, Any] | None = field(init=False, default=None)
    purchase_confirmed: bool = field(init=False, default=False)

    def build_initial_request(self, merchant_name: str) -> "A2AMessage":
        """Craft the first message that asks the merchant for product details."""

        self._state = "awaiting_product"
        from a2a.protocol import A2AMessage  # Imported lazily to avoid cycles.

        return A2AMessage(
            sender=self.name,
            recipient=merchant_name,
            content={
                "intent": "find_product",
                "query": self.desired_sku,
            },
        )

    @property
    def order_summary(self) -> Mapping[str, Any] | None:
        """Return a summary once the purchase is confirmed."""

        if not self.purchase_confirmed or not self._product or self._shipping_cost is None:
            return None

        total_cost = round((self._product.get("price", 0.0) * self.quantity) + self._shipping_cost, 2)
        return {
            "sku": self.desired_sku,
            "quantity": self.quantity,
            "product": dict(self._product),
            "shipping_cost": self._shipping_cost,
            "total_cost": total_cost,
        }

    @property
    def last_error(self) -> Mapping[str, Any] | None:
        """Expose the latest error payload for diagnostics."""

        return self._last_error

    async def handle_message(self, message: "A2AMessage", history: Sequence["A2AMessage"]):
        """Process merchant replies and return follow-up requests when needed."""

        payload = message.content
        if not isinstance(payload, Mapping):
            self._last_error = {"error": "Received non-structured payload", "payload": payload}
            self._state = "failed"
            return {
                "intent": "terminate",
                "reason": "Merchant reply was not structured as a mapping.",
            }

        intent = payload.get("intent")
        if intent == "find_product_result":
            return await self._handle_product_result(payload)
        if intent == "calc_shipping_result":
            return await self._handle_shipping_result(payload)
        if intent == "reserve_stock_result":
            return await self._handle_reservation_result(payload)
        if intent == "acknowledge":
            # Merchant confirmed termination or completion; nothing else to do.
            self._state = "completed"
            return None
        if intent == "error":
            self._last_error = payload
            self._state = "failed"
            return None

        # Unrecognised message types abort the conversation politely.
        self._last_error = payload
        self._state = "failed"
        return {
            "intent": "terminate",
            "reason": f"Unsupported merchant intent: {intent}",
        }

    async def _handle_product_result(self, payload: Mapping[str, Any]):
        result = payload.get("result", {})
        if result.get("status") != Status.SUCCESS.value or not result.get("data"):
            self._state = "failed"
            self._last_error = result
            raw_reason = result.get("message", "")
            reason = raw_reason if raw_reason and raw_reason != "SUCCESS" else "Product is unavailable."
            return {
                "intent": "terminate",
                "reason": reason,
            }

        self._product = result["data"][0]
        self._state = "awaiting_shipping"
        return {
            "intent": "calc_shipping",
            "weight": self.shipping_weight,
            "distance": self.shipping_distance,
        }

    async def _handle_shipping_result(self, payload: Mapping[str, Any]):
        result = payload.get("result", {})
        if result.get("status") != Status.SUCCESS.value:
            self._state = "failed"
            self._last_error = result
            return {
                "intent": "terminate",
                "reason": result.get("message", "Unable to compute shipping."),
            }

        cost = float(result.get("data", 0.0))
        self._shipping_cost = cost
        if self.budget is not None and cost > self.budget:
            self._state = "failed"
            return {
                "intent": "terminate",
                "reason": "Shipping cost exceeds customer budget.",
                "shipping_cost": cost,
            }

        self._state = "awaiting_reservation"
        return {
            "intent": "reserve_stock",
            "sku": self.desired_sku,
            "quantity": self.quantity,
        }

    async def _handle_reservation_result(self, payload: Mapping[str, Any]):
        result = payload.get("result", {})
        if result.get("status") == Status.SUCCESS.value and result.get("data"):
            self._state = "completed"
            self.purchase_confirmed = True
            summary = self.order_summary or {}
            return {
                "intent": "confirm_order",
                "sku": summary.get("sku", self.desired_sku),
                "quantity": summary.get("quantity", self.quantity),
                "shipping_cost": summary.get("shipping_cost", self._shipping_cost),
                "total_cost": summary.get("total_cost"),
            }

        self._state = "failed"
        self.purchase_confirmed = False
        self._last_error = result
        return {
            "intent": "terminate",
            "reason": result.get("message", "Reservation failed."),
            "status": result.get("status"),
        }
