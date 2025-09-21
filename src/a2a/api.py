"""HTTP-friendly service layer for orchestrating shopping sessions."""

from __future__ import annotations

from typing import Any, Mapping

from a2a.session import ShoppingA2ASession
from merchant_agent.mcp_client import MCPServiceClient, MCPServiceError
from merchant_agent.rule_based import RuleBasedMerchantAgent
from shopping_agent.rule_based import RuleBasedShoppingAgent
from utils.app_string import (
    INVALID_REQUEST_PAYLOAD,
    SESSION_COMPLETED,
    SESSION_FAILED,
    SUCCESS,
    UNKNOWN_ENDPOINT,
    UPSTREAM_SERVICE_ERROR,
)
from utils.response_format import ResponseFormat
from utils.status import Status
from utils.urls import SHOPPING_URLS


class ShoppingService:
    """Service facade used by both HTTP handlers and tests."""

    def __init__(self, mcp_client: MCPServiceClient | None = None):
        self._mcp_client = mcp_client or MCPServiceClient()

    async def dispatch(self, method: str, path: str, payload: Mapping[str, Any] | None) -> tuple[int, Any]:
        if method == "GET" and path == SHOPPING_URLS.health:
            body = ResponseFormat(
                status=Status.SUCCESS,
                message=SUCCESS,
                data={"service": "shopping_api"},
            )
            return 200, body.to_dict()
        if method == "POST" and path == SHOPPING_URLS.sessions:
            return await self._handle_session(payload or {})
        body = ResponseFormat(
            status=Status.UNKNOWN_ENDPOINT,
            message=UNKNOWN_ENDPOINT,
            data={"path": path},
        )
        return 404, body.to_dict()

    async def _handle_session(self, payload: Mapping[str, Any]) -> tuple[int, Any]:
        valid, response = self._validate_payload(payload)
        if not valid:
            return 400, response.to_dict()

        request = response.data or {}
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
            body = ResponseFormat(
                status=Status.UPSTREAM_SERVICE_ERROR,
                message=f"{UPSTREAM_SERVICE_ERROR}: {exc}",
                data={
                    "status_code": exc.status_code,
                    "details": exc.details,
                },
            )
            return 502, body.to_dict()

        session_status = customer.purchase_confirmed
        status = Status.SUCCESS if session_status else Status.FAILURE
        message = SESSION_COMPLETED if session_status else SESSION_FAILED
        body = ResponseFormat(
            status=status,
            message=message,
            data={
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
            },
        )
        return 200, body.to_dict()

    def _validate_payload(self, payload: Mapping[str, Any]) -> tuple[bool, ResponseFormat]:
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
                message = f"{INVALID_REQUEST_PAYLOAD}: missing field '{field}'"
                return False, ResponseFormat(
                    status=Status.INVALID_REQUEST,
                    message=message,
                    data={"field": field, "issue": "missing"},
                )
            if not isinstance(value, expected_type):
                message = f"{INVALID_REQUEST_PAYLOAD}: field '{field}' must be of type {expected_type}."
                return False, ResponseFormat(
                    status=Status.INVALID_REQUEST,
                    message=message,
                    data={"field": field, "issue": "invalid_type"},
                )
            validated[field] = value

        if validated["quantity"] <= 0:
            return False, ResponseFormat(
                status=Status.INVALID_REQUEST,
                message=f"{INVALID_REQUEST_PAYLOAD}: quantity must be greater than zero.",
                data={"field": "quantity", "issue": "out_of_range"},
            )
        if validated["shipping_weight"] < 0 or validated["shipping_distance"] < 0:
            return False, ResponseFormat(
                status=Status.INVALID_REQUEST,
                message=f"{INVALID_REQUEST_PAYLOAD}: shipping weight and distance must be non-negative.",
                data={"field": "shipping", "issue": "out_of_range"},
            )

        budget = payload.get("budget")
        if budget is not None:
            if not isinstance(budget, (int, float)) or budget < 0:
                return False, ResponseFormat(
                    status=Status.INVALID_REQUEST,
                    message=f"{INVALID_REQUEST_PAYLOAD}: budget must be a non-negative number.",
                    data={"field": "budget", "issue": "invalid_value"},
                )
            validated["budget"] = float(budget)

        validated["quantity"] = int(validated["quantity"])
        validated["shipping_weight"] = float(validated["shipping_weight"])
        validated["shipping_distance"] = float(validated["shipping_distance"])
        validated["sku"] = str(validated["sku"])

        return True, ResponseFormat(status=Status.SUCCESS, message=SUCCESS, data=validated)


def create_app(mcp_client: MCPServiceClient | None = None) -> ShoppingService:
    """Retained for backwards compatibility with previous FastAPI factory."""

    return ShoppingService(mcp_client=mcp_client)


__all__ = ["ShoppingService", "create_app"]
