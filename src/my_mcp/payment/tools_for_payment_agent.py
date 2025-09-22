from typing import Optional, Any

from google.adk.tools import FunctionTool

from my_a2a.payment_schemas.payment_enums import *
from my_a2a.payment_schemas.next_action import NextAction
from my_a2a.payment_schemas.payment_request import PaymentRequest
from my_a2a.payment_schemas.payment_response import PaymentResponse


async def _stub_paygate_create(provider: str, channel: PaymentChannel, total: float, return_url: Optional[str], cancel_url: Optional[str]):
    import time, uuid
    oid = f"{provider}_{uuid.uuid4().hex[:12]}"
    exp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 15*60))
    if channel == PaymentChannel.REDIRECT:
        return {"order_id": oid, "pay_url": f"https://{provider}.pay/checkout/{oid}", "expires_at": exp}
    return {"order_id": oid, "qr_image_url": f"https://{provider}.pay/qr/{oid}.png", "expires_at": exp}


async def create_order(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Create a payment order on a payment paygate and return next_action for the customer.
    Args:
      payload: {
        "correlation_id": "...",
        "items": [{sku,name,quantity,unit_price,currency}],
        "customer": {...},
        "method": {"provider": "...", "channel": "redirect|qr", "return_url"?, "cancel_url"?}
      }
    Returns: PaymentResponse dict (status=PENDING + next_action=REDIRECT|SHOW_QR)
    """
    req = PaymentRequest.model_validate({
        "correlation_id": payload["correlation_id"],
        "items": payload["items"],
        "customer": payload.get("customer", {}),
        "method": payload.get("method", {}),
        "action": PaymentAction.CREATE_ORDER,
    })
    total = sum(i.quantity * i.unit_price for i in req.items)
    paygate_response = await _stub_paygate_create(req.method.provider, req.method.channel, total, req.method.return_url, req.method.cancel_url)

    if req.method.channel == PaymentChannel.REDIRECT:
        next_action = NextAction(
            type=NextActionType.REDIRECT,
            url=paygate_response["pay_url"],
            expires_at=paygate_response["expires_at"]
        )
    else:
        next_action = NextAction(
            type=NextActionType.SHOW_QR,
            qr_code_url=paygate_response["qr_code_url"],
            expires_at=paygate_response["expires_at"]
        )

    res = PaymentResponse(
        correlation_id=req.correlation_id,
        status=PaymentStatus.PENDING,
        paygate=req.method.provider,
        order_id=paygate_response["order_id"],
        pay_url=paygate_response.get("pay_url"),
        qr_code_url=paygate_response.get("qr_image_url"),
        expires_at=paygate_response["expires_at"],
        next_action=next_action,
    )
    return res.model_dump()


async def query_order_status(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Query order status by correlation_id
    Args:
      payload: {"correlation_id": "..."}
    """
    cid = payload["correlation_id"]
    snap = _recall(cid)
    if not snap:
        return PaymentResponse(correlation_id=cid, status=PaymentStatus.FAILED).model_dump()
    return snap


_MEMORY: dict[str, dict[str, Any]] = {}
def _remember(correlation_id: str, snapshot: dict[str, Any]): _MEMORY[correlation_id] = snapshot
def _recall(correlation_id: str) -> Optional[dict[str, Any]]: return _MEMORY.get(correlation_id)


async def create_order_stateful(payload: dict[str, Any]) -> dict[str, Any]:
    res = await create_order(payload)
    _remember(res["correlation_id"], res)
    return res


print("Initializing ADK tool for payment...")
create_order_tool = FunctionTool(create_order)
query_order_status_tool = FunctionTool(query_order_status)
ADK_TOOLS_FOR_PAYMENT = {
    create_order_tool.name: create_order_tool,
    query_order_status_tool.name: query_order_status_tool,
}
for adk_tool in ADK_TOOLS_FOR_PAYMENT.values():
    print(f"ADK tool '{adk_tool.name}' initialized and ready to be exposed via MCP.")
