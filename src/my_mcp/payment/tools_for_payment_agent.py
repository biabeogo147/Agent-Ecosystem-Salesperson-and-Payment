from typing import Optional, Any

from google.adk.tools import FunctionTool

from . import payment_mcp_logger

from src.config import *
from src.data.db_connection import db_connection
from src.data.models.db_entity.order import Order
from src.data.models.enum.order_status import OrderStatus
from src.my_agent.my_a2a_common.payment_schemas.payment_enums import *
from src.my_agent.my_a2a_common.payment_schemas.next_action import NextAction
from src.my_agent.my_a2a_common.payment_schemas.payment_response import PaymentResponse
from src.utils.response_format import ResponseFormat
from src.utils.status import Status


def _map_order_status_to_payment_status(order_status: OrderStatus) -> PaymentStatus:
    """Map OrderStatus to PaymentStatus."""
    mapping = {
        OrderStatus.PENDING: PaymentStatus.PENDING,
        OrderStatus.SUCCESS: PaymentStatus.SUCCESS,
        OrderStatus.PAID: PaymentStatus.SUCCESS,
        OrderStatus.FAILED: PaymentStatus.FAILED,
        OrderStatus.CANCELLED: PaymentStatus.CANCELLED,
    }
    return mapping.get(order_status, PaymentStatus.PENDING)


async def _stub_paygate_create(channel: PaymentChannel, total: float, return_url: Optional[str], cancel_url: Optional[str]):
    import time, uuid
    oid = str(uuid.uuid4())
    exp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 15*60))
    if channel == PaymentChannel.REDIRECT.value:
        return {"order_id": oid, "pay_url": f"{CHECKOUT_URL}/{oid}", "expires_at": exp}
    return {"order_id": oid, "qr_code_url": f"{QR_URL}/{oid}.png", "expires_at": exp}


async def create_order(payload: dict[str, Any]) -> str:
    """
    Create a payment order and save to database.
    Args:
      payload: {
        "product_sku": "SKU001",
        "quantity": 1,
        "user_id": 123 (optional),
        "method": {"channel": "redirect|qr", "return_url", "cancel_url"}
      }
    Returns: PaymentResponse with order_id and next_action
    """
    session = db_connection.get_session()
    try:
        # Get product info
        from src.data.models.db_entity.product import Product
        product = session.query(Product).filter(Product.sku == payload["product_sku"]).first()
        if not product:
            return ResponseFormat(status=Status.PRODUCT_NOT_FOUND, message="Product not found").to_json()

        quantity = payload.get("quantity", 1)
        total_amount = float(product.price) * quantity

        # Create order in DB
        order = Order(
            user_id=payload.get("user_id"),
            product_sku=payload["product_sku"],
            quantity=quantity,
            total_amount=total_amount,
            currency=product.currency,
            status=OrderStatus.PENDING
        )
        session.add(order)
        session.commit()
        session.refresh(order)

        # Call payment gateway
        method = payload.get("method", {})
        channel = method.get("channel", PaymentChannel.REDIRECT.value)
        paygate_response = await _stub_paygate_create(
            channel, total_amount,
            method.get("return_url"), method.get("cancel_url")
        )

        # Build next_action
        if channel == PaymentChannel.REDIRECT.value:
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
            context_id=str(order.id),
            status=PaymentStatus.PENDING,
            provider_name=PAYGATE_PROVIDER,
            order_id=str(order.id),
            pay_url=paygate_response.get("pay_url"),
            qr_code_url=paygate_response.get("qr_code_url"),
            expires_at=paygate_response["expires_at"],
            next_action=next_action,
        )
        return ResponseFormat(data=res.model_dump()).to_json()
    except Exception as e:
        session.rollback()
        return ResponseFormat(status=Status.UNKNOWN_ERROR, message=str(e)).to_json()
    finally:
        session.close()


async def query_order_status(payload: dict[str, Any]) -> str:
    """
    Query order status from database.
    Args:
      payload: {"order_id": "123"}
    Returns: Order details with current status
    """
    session = db_connection.get_session()
    try:
        order_id = payload.get("order_id")
        order = session.query(Order).filter(Order.id == int(order_id)).first()

        if not order:
            return ResponseFormat(status=Status.ORDER_NOT_FOUND, message="Order not found").to_json()

        res = PaymentResponse(
            context_id=str(order.id),
            status=_map_order_status_to_payment_status(order.status),
            order_id=str(order.id),
        )
        return ResponseFormat(data={**res.model_dump(), "order": order.to_dict()}).to_json()
    except Exception as e:
        return ResponseFormat(status=Status.UNKNOWN_ERROR, message=str(e)).to_json()
    finally:
        session.close()


async def update_order_status(payload: dict[str, Any]) -> str:
    """
    Update order status (called by payment webhook or manual update).
    Args:
      payload: {"order_id": "123", "status": "paid|failed|cancelled"}
    Returns: Updated order
    """
    session = db_connection.get_session()
    try:
        order_id = payload.get("order_id")
        new_status = payload.get("status")

        order = session.query(Order).filter(Order.id == int(order_id)).first()
        if not order:
            return ResponseFormat(status=Status.ORDER_NOT_FOUND, message="Order not found").to_json()

        order.status = OrderStatus(new_status)
        session.commit()
        session.refresh(order)

        return ResponseFormat(data=order.to_dict()).to_json()
    except Exception as e:
        session.rollback()
        return ResponseFormat(status=Status.UNKNOWN_ERROR, message=str(e)).to_json()
    finally:
        session.close()


payment_mcp_logger.info("Initializing ADK tool for payment...")
create_order_tool = FunctionTool(create_order)
query_order_status_tool = FunctionTool(query_order_status)
update_order_status_tool = FunctionTool(update_order_status)

ADK_TOOLS_FOR_PAYMENT = {
    create_order_tool.name: create_order_tool,
    query_order_status_tool.name: query_order_status_tool,
    update_order_status_tool.name: update_order_status_tool,
}

for adk_tool in ADK_TOOLS_FOR_PAYMENT.values():
    payment_mcp_logger.info(f"ADK tool '{adk_tool.name}' initialized and ready to be exposed via MCP.")