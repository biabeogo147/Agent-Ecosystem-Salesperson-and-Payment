from typing import Optional, Any

from google.adk.tools import FunctionTool

from config import *
from my_a2a_common.payment_schemas.payment_enums import *
from my_a2a_common.payment_schemas.next_action import NextAction
from my_a2a_common.payment_schemas.payment_request import PaymentRequest
from my_a2a_common.payment_schemas.payment_response import PaymentResponse
from utils.response_format import ResponseFormat


async def _stub_paygate_create(channel: PaymentChannel, total: float, return_url: Optional[str], cancel_url: Optional[str]):
    import time, uuid
    oid = str(uuid.uuid4())
    exp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 15*60))
    if channel == PaymentChannel.REDIRECT.value:
        return {"order_id": oid, "pay_url": f"{CHECKOUT_URL}/{oid}", "expires_at": exp}
    return {"order_id": oid, "qr_code_url": f"{QR_URL}/{oid}.png", "expires_at": exp}


async def create_order(payload: dict[str, Any]) -> str:
    """
    Create a payment order on a payment paygate and return next_action for the customer.
    Args:
      payload: {
        "context_id": "...",
        "items": [{sku,name,quantity,unit_price,currency}],
        "customer": {...},
        "method": {"channel": "redirect|qr", "return_url", "cancel_url"}
      }
    Returns: PaymentResponse dict (status=PENDING + next_action=REDIRECT|SHOW_QR)
    """
    req = PaymentRequest.model_validate({
        "context_id": payload["context_id"],
        "items": payload["items"],
        "customer": payload.get("customer", {}),
        "method": payload.get("method", {}),
        "action": PaymentAction.CREATE_ORDER,
    })
    total = sum(i.quantity * i.unit_price for i in req.items)
    paygate_response = await _stub_paygate_create(req.method.channel, total, req.method.return_url, req.method.cancel_url)

    if req.method.channel == PaymentChannel.REDIRECT.value:
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
        context_id=req.context_id,
        status=PaymentStatus.PENDING,
        provider_name=PAYGATE_PROVIDER,
        order_id=paygate_response["order_id"],
        pay_url=paygate_response.get("pay_url"),
        qr_code_url=paygate_response.get("qr_code_url"),
        expires_at=paygate_response["expires_at"],
        next_action=next_action,
    )
    return ResponseFormat(data=res.model_dump()).to_json()


async def query_order_status(payload: dict[str, Any]) -> str:
    """
    Query order status by context_id
    Args:
      payload: {"context_id": "..."}
    """
    cid = payload["context_id"]
    res = PaymentResponse(context_id=cid, status=PaymentStatus.FAILED)
    return ResponseFormat(data=res.model_dump()).to_json()


print("Initializing ADK tool for payment...")
create_order_tool = FunctionTool(create_order)
query_order_status_tool = FunctionTool(query_order_status)
ADK_TOOLS_FOR_PAYMENT = {
    create_order_tool.name: create_order_tool,
    query_order_status_tool.name: query_order_status_tool,
}
for adk_tool in ADK_TOOLS_FOR_PAYMENT.values():
    print(f"ADK tool '{adk_tool.name}' initialized and ready to be exposed via MCP.")
