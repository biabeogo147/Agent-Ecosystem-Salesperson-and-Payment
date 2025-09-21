"""Rule-based merchant agent that exposes MCP tools through A2A messages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .mcp_client import MCPServiceClient, MCPServiceError


@dataclass
class RuleBasedMerchantAgent:
    """Sales assistant that answers structured customer requests."""

    name: str = "merchant_agent"
    mcp_client: MCPServiceClient = field(default_factory=MCPServiceClient)

    async def handle_message(self, message: "A2AMessage", history: Sequence["A2AMessage"]):
        payload = message.content
        if not isinstance(payload, Mapping):
            return {
                "intent": "error",
                "message": "Payload must be a mapping of intent and parameters.",
            }

        intent = payload.get("intent")
        if intent == "find_product":
            return await self._handle_find_product(payload)
        if intent == "calc_shipping":
            return await self._handle_calc_shipping(payload)
        if intent == "reserve_stock":
            return await self._handle_reserve_stock(payload)
        if intent == "confirm_order":
            return {
                "intent": "acknowledge",
                "status": "order_confirmed",
                "order": {
                    "sku": payload.get("sku"),
                    "quantity": payload.get("quantity"),
                    "shipping_cost": payload.get("shipping_cost"),
                    "total_cost": payload.get("total_cost"),
                },
            }
        if intent == "terminate":
            return {
                "intent": "acknowledge",
                "status": "terminated",
                "reason": payload.get("reason", "Conversation closed by customer."),
            }

        return {
            "intent": "error",
            "message": f"Unknown intent '{intent}' received from {message.sender}.",
        }

    async def _handle_find_product(self, payload: Mapping[str, Any]):
        query = str(payload.get("query", ""))
        invocation = await self._call_tool("find_product", payload, {"query": query})
        if invocation.get("intent") == "error":
            return invocation

        result, raw = self._extract_result(invocation)
        response: dict[str, Any] = {
            "intent": "find_product_result",
            "query": query,
            "result": result,
        }
        if raw is not None:
            response["raw_response"] = raw
        return response

    async def _handle_calc_shipping(self, payload: Mapping[str, Any]):
        weight = float(payload.get("weight", 0))
        distance = float(payload.get("distance", 0))
        invocation = await self._call_tool(
            "calc_shipping",
            payload,
            {"weight": weight, "distance": distance},
        )
        if invocation.get("intent") == "error":
            return invocation

        result, raw = self._extract_result(invocation)
        response: dict[str, Any] = {
            "intent": "calc_shipping_result",
            "weight": weight,
            "distance": distance,
            "result": result,
        }
        if raw is not None:
            response["raw_response"] = raw
        return response

    async def _handle_reserve_stock(self, payload: Mapping[str, Any]):
        sku = str(payload.get("sku", ""))
        quantity = int(payload.get("quantity", 0))
        invocation = await self._call_tool(
            "reserve_stock",
            payload,
            {"sku": sku, "quantity": quantity},
        )
        if invocation.get("intent") == "error":
            return invocation

        result, raw = self._extract_result(invocation)
        response: dict[str, Any] = {
            "intent": "reserve_stock_result",
            "sku": sku,
            "quantity": quantity,
            "result": result,
        }
        if raw is not None:
            response["raw_response"] = raw
        return response

    async def _call_tool(
        self,
        tool_name: str,
        original_payload: Mapping[str, Any],
        arguments: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        try:
            response = await self.mcp_client.call_tool(tool_name, arguments)
            data = response.get("data") if isinstance(response, Mapping) else None
            payload: dict[str, Any] = {
                "status": response.get("status") if isinstance(response, Mapping) else None,
                "message": response.get("message") if isinstance(response, Mapping) else None,
                "tool": tool_name,
                "result": None,
            }
            if isinstance(data, Mapping):
                payload["tool"] = data.get("tool", tool_name)
                payload["result"] = data.get("result")
                raw = data.get("raw")
                if raw is not None:
                    payload["raw"] = raw
            else:
                payload["result"] = data
            return payload
        except MCPServiceError as exc:
            error_payload: dict[str, Any] = {
                "intent": "error",
                "message": f"Unable to execute MCP tool '{tool_name}': {exc}",
                "tool": tool_name,
                "failed_intent": original_payload.get("intent"),
            }
            if exc.status_code is not None:
                error_payload["status_code"] = exc.status_code
            if exc.details is not None:
                error_payload["details"] = exc.details
            return error_payload

    def _extract_result(self, invocation: Mapping[str, Any]) -> tuple[Mapping[str, Any], Any | None]:
        result = invocation.get("result")
        raw = invocation.get("raw")
        if isinstance(result, Mapping):
            return result, raw
        return {
            "status": "unknown",
            "message": "MCP service returned a non-structured payload.",
            "data": result,
        }, raw


__all__ = ["RuleBasedMerchantAgent"]
