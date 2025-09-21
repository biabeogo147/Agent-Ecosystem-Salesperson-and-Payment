"""HTTP-friendly service layer for orchestrating shopping sessions."""

from __future__ import annotations

from typing import Any, Mapping

from a2a.session import ShoppingA2ASession
from merchant_agent.mcp_client import MCPServiceClient, MCPServiceError
from merchant_agent.rule_based import RuleBasedMerchantAgent
from shopping_agent.rule_based import RuleBasedShoppingAgent


class ShoppingService:
    """Service facade used by both HTTP handlers and tests."""

    def __init__(self, mcp_client: MCPServiceClient | None = None):
        self._mcp_client = mcp_client or MCPServiceClient()

    async def dispatch(self, method: str, path: str, payload: Mapping[str, Any] | None) -> tuple[int, Any]:
        if method == "GET" and path == "/healthz":
            return 200, {"status": "ok"}
        if method == "POST" and path == "/v1/sessions":
            return await self._handle_session(payload or {})
        return 404, {"status": "error", "message": "Unknown endpoint."}

    async def _handle_session(self, payload: Mapping[str, Any]) -> tuple[int, Any]:
        valid, error = self._validate_payload(payload)
        if not valid:
            return 400, error

        request = error  # error contains the validated payload when valid is True
        customer = RuleBasedShoppingAgent(
            desired_sku=request["sku"],
            quantity=request["quantity"],
            shipping_weight=request["shipping_weight"],
            shipping_distance=request["shipping_distance"],
            budget=request.get("budget"),
        )
        merchant = RuleBasedMerchantAgent(mcp_client=self._mcp_client)
        session = ShoppingA2ASession(customer=customer, merchant=merchant)

        try:
            transcript = await session.start()
        except MCPServiceError as exc:
            return 502, {"status": "error", "message": str(exc)}

        status = "success" if customer.purchase_confirmed else "failed"
        body = {
            "status": status,
            "summary": customer.order_summary,
            "last_error": customer.last_error,
            "transcript": [
                {
                    "sender": message.sender,
                    "recipient": message.recipient,
                    "content": message.content,
                    "metadata": message.metadata,
                }
                for message in transcript
            ],
        }
        return 200, body

    def _validate_payload(self, payload: Mapping[str, Any]) -> tuple[bool, Mapping[str, Any]]:
        required_fields = {
            "sku": str,
            "quantity": int,
            "shipping_weight": (int, float),
            "shipping_distance": (int, float),
        }
        validated: dict[str, Any] = {}

        for field, expected_type in required_fields.items():
            value = payload.get(field)
            if value is None:
                return False, {"status": "error", "message": f"Missing field '{field}'."}
            if not isinstance(value, expected_type):
                return False, {
                    "status": "error",
                    "message": f"Field '{field}' must be of type {expected_type}.",
                }
            validated[field] = value

        if validated["quantity"] <= 0:
            return False, {"status": "error", "message": "Quantity must be greater than zero."}
        if validated["shipping_weight"] < 0 or validated["shipping_distance"] < 0:
            return False, {
                "status": "error",
                "message": "Shipping weight and distance must be non-negative.",
            }

        budget = payload.get("budget")
        if budget is not None:
            if not isinstance(budget, (int, float)) or budget < 0:
                return False, {"status": "error", "message": "Budget must be a non-negative number."}
            validated["budget"] = float(budget)

        validated["quantity"] = int(validated["quantity"])
        validated["shipping_weight"] = float(validated["shipping_weight"])
        validated["shipping_distance"] = float(validated["shipping_distance"])
        validated["sku"] = str(validated["sku"])

        return True, validated


def create_app(mcp_client: MCPServiceClient | None = None) -> ShoppingService:
    """Retained for backwards compatibility with previous FastAPI factory."""

    return ShoppingService(mcp_client=mcp_client)


__all__ = ["ShoppingService", "create_app"]
