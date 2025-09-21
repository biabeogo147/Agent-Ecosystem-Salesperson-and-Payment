"""Shopping session service that orchestrates MCP tool invocations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from merchant_agent.mcp_client import MCPServiceClient, MCPServiceError
from merchant_agent.urls import SHOPPING_URLS
from utils.app_string import (
    INVALID_REQUEST_PAYLOAD,
    PRODUCT_NOT_FOUND,
    SESSION_COMPLETED,
    SESSION_FAILED,
    SUCCESS,
    UNKNOWN_ENDPOINT,
    UPSTREAM_SERVICE_ERROR,
)
from utils.response_format import ResponseFormat
from utils.status import Status


@dataclass
class ShoppingSessionService:
    """Coordinate the order fulfilment flow by calling MCP tools."""

    mcp_client: MCPServiceClient = field(default_factory=MCPServiceClient)

    async def dispatch(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None,
    ) -> tuple[int, Mapping[str, Any]]:
        if method == "POST" and path == SHOPPING_URLS.sessions:
            if payload is None or not isinstance(payload, Mapping):
                body = ResponseFormat(
                    status=Status.INVALID_REQUEST,
                    message=f"{INVALID_REQUEST_PAYLOAD}: payload must be an object.",
                    data=None,
                )
                return 400, body.to_dict()
            return await self._create_session(dict(payload))

        body = ResponseFormat(
            status=Status.UNKNOWN_ENDPOINT,
            message=UNKNOWN_ENDPOINT,
            data={"path": path},
        )
        return 404, body.to_dict()

    async def _create_session(self, payload: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
        sku = str(payload.get("sku", "")).strip()
        quantity = int(payload.get("quantity", 0) or 0)
        weight = float(payload.get("shipping_weight", 0.0) or 0.0)
        distance = float(payload.get("shipping_distance", 0.0) or 0.0)

        transcript: list[Mapping[str, Any]] = [
            {
                "role": "customer",
                "content": {
                    "intent": "order_request",
                    "sku": sku,
                    "quantity": quantity,
                    "shipping_weight": weight,
                    "shipping_distance": distance,
                },
            }
        ]

        if not sku or quantity <= 0:
            return self._failure(
                transcript,
                "Invalid order request.",
                details={"sku": sku, "quantity": quantity},
            )

        product_response = await self._call_tool(
            "find_product",
            {"query": sku},
            transcript,
            error_hint={"sku": sku},
        )
        if product_response is None:
            return self._finalise_failure(transcript)
        product_result, _ = product_response
        product_entries = self._coerce_list(product_result.get("data"))
        if not product_entries:
            return self._failure(
                transcript,
                PRODUCT_NOT_FOUND,
                details={"sku": sku},
            )

        product_info = product_entries[0]
        transcript.append(
            {
                "role": "agent",
                "content": {"intent": "find_product_result", "result": product_entries},
            }
        )

        shipping_response = await self._call_tool(
            "calc_shipping",
            {"weight": weight, "distance": distance},
            transcript,
            error_hint={"sku": sku},
        )
        if shipping_response is None:
            return self._finalise_failure(transcript)
        shipping_result, _ = shipping_response
        shipping_data = shipping_result.get("data")
        shipping_cost = round(float(shipping_data or 0.0), 2)
        transcript.append(
            {
                "role": "agent",
                "content": {"intent": "calc_shipping_result", "amount": shipping_cost},
            }
        )

        reserve_response = await self._call_tool(
            "reserve_stock",
            {"sku": sku, "quantity": quantity},
            transcript,
            error_hint={"sku": sku, "quantity": quantity},
        )
        if reserve_response is None:
            return self._finalise_failure(transcript)
        reserve_result, _ = reserve_response
        reserved = bool(reserve_result.get("data"))
        if not reserved:
            return self._failure(
                transcript,
                reserve_result.get("message", SESSION_FAILED),
                details={"sku": sku, "quantity": quantity},
            )

        transcript.append(
            {
                "role": "agent",
                "content": {"intent": "reserve_stock_result", "reserved": True},
            }
        )

        unit_price = float(product_info.get("price", 0.0) or 0.0)
        subtotal = round(unit_price * quantity, 2)
        total_cost = round(subtotal + shipping_cost, 2)
        summary = {
            "sku": product_info.get("sku", sku),
            "name": product_info.get("name"),
            "quantity": quantity,
            "unit_price": unit_price,
            "currency": product_info.get("currency", "USD"),
            "shipping_cost": shipping_cost,
            "subtotal": subtotal,
            "total_cost": total_cost,
        }

        transcript.append(
            {
                "role": "agent",
                "content": {
                    "intent": "confirm_order",
                    "sku": summary["sku"],
                    "quantity": quantity,
                    "shipping_cost": shipping_cost,
                    "total_cost": total_cost,
                },
            }
        )

        body = ResponseFormat(
            status=Status.SUCCESS,
            message=SESSION_COMPLETED,
            data={
                "summary": summary,
                "transcript": transcript,
                "last_error": None,
            },
        )
        return 200, body.to_dict()

    async def _call_tool(
        self,
        tool_name: str,
        arguments: Mapping[str, Any],
        transcript: list[Mapping[str, Any]],
        *,
        error_hint: Mapping[str, Any] | None = None,
    ) -> tuple[Mapping[str, Any], Any] | None:
        try:
            response = await self.mcp_client.call_tool(tool_name, arguments)
        except MCPServiceError as exc:
            transcript.append(
                {
                    "role": "agent",
                    "content": {
                        "intent": "error",
                        "message": f"{UPSTREAM_SERVICE_ERROR}: {exc}",
                        "tool": tool_name,
                        "details": dict(error_hint or {}),
                    },
                }
            )
            return None

        status = response.get("status")
        if status != Status.SUCCESS.value:
            transcript.append(
                {
                    "role": "agent",
                    "content": {
                        "intent": "error",
                        "message": response.get("message", SESSION_FAILED),
                        "tool": tool_name,
                        "details": dict(error_hint or {}),
                    },
                }
            )
            return None

        data = response.get("data")
        if not isinstance(data, Mapping):
            transcript.append(
                {
                    "role": "agent",
                    "content": {
                        "intent": "error",
                        "message": UPSTREAM_SERVICE_ERROR,
                        "tool": tool_name,
                        "details": dict(error_hint or {}),
                    },
                }
            )
            return None

        result = data.get("result")
        if isinstance(result, Mapping):
            inner_status = result.get("status", Status.SUCCESS.value)
            if inner_status != Status.SUCCESS.value:
                transcript.append(
                    {
                        "role": "agent",
                        "content": {
                            "intent": "error",
                            "message": result.get("message", SESSION_FAILED),
                            "tool": tool_name,
                            "details": dict(error_hint or {}),
                        },
                    }
                )
                return None
        else:
            result = {
                "status": Status.SUCCESS.value,
                "message": response.get("message", SUCCESS),
                "data": result,
            }

        raw = data.get("raw") if isinstance(data, Mapping) else None
        return result, raw

    def _failure(
        self,
        transcript: list[Mapping[str, Any]],
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
        status: Status = Status.FAILURE,
        failure_message: str | None = None,
    ) -> tuple[int, Mapping[str, Any]]:
        error_content = {
            "intent": "error",
            "message": message,
        }
        if details:
            error_content["details"] = dict(details)
        transcript.append({"role": "agent", "content": error_content})
        return self._finalise_failure(
            transcript,
            status=status,
            failure_message=failure_message or SESSION_FAILED,
        )

    def _finalise_failure(
        self,
        transcript: list[Mapping[str, Any]],
        *,
        status: Status = Status.FAILURE,
        failure_message: str | None = None,
    ) -> tuple[int, Mapping[str, Any]]:
        last_error = None
        if transcript:
            last_entry = transcript[-1]
            content = last_entry.get("content") if isinstance(last_entry, Mapping) else None
            if isinstance(content, Mapping) and content.get("intent") == "error":
                last_error = content
        if last_error is None:
            last_error = {"intent": "error", "message": failure_message or SESSION_FAILED}
            transcript.append({"role": "agent", "content": last_error})
        body = ResponseFormat(
            status=status,
            message=failure_message or SESSION_FAILED,
            data={
                "summary": None,
                "transcript": transcript,
                "last_error": last_error,
            },
        )
        return 200, body.to_dict()

    @staticmethod
    def _coerce_list(value: Any) -> list[Any]:
        if isinstance(value, list):
            return value
        if value is None:
            return []
        return [value]


def create_app(mcp_client: MCPServiceClient | None = None) -> ShoppingSessionService:
    """Factory that mirrors the pattern used by other services."""

    return ShoppingSessionService(mcp_client=mcp_client or MCPServiceClient())


__all__ = ["ShoppingSessionService", "create_app"]
