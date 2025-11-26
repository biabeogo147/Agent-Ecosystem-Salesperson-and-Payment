import time
from typing import Optional, Any

from google.adk.tools import FunctionTool

from . import payment_mcp_logger

from src.config import *

from src.data.models.db_entity.order import Order
from src.data.postgres.connection import db_connection
from src.data.models.enum.order_status import OrderStatus

from src.my_agent.my_a2a_common.payment_schemas.payment_enums import *
from src.my_agent.my_a2a_common.payment_schemas.next_action import NextAction
from src.my_agent.my_a2a_common.payment_schemas.payment_response import PaymentResponse

from src.utils.status import Status
from src.utils.response_format import ResponseFormat


def _map_order_status_to_payment_status(order_status: OrderStatus) -> PaymentStatus:
    mapping = {
        OrderStatus.PENDING: PaymentStatus.PENDING,
        OrderStatus.SUCCESS: PaymentStatus.SUCCESS,
        OrderStatus.PAID: PaymentStatus.SUCCESS,
        OrderStatus.FAILED: PaymentStatus.FAILED,
        OrderStatus.CANCELLED: PaymentStatus.CANCELLED,
    }
    return mapping.get(order_status, PaymentStatus.PENDING)


async def _stub_paygate_create(
        channel: PaymentChannel, oid: int, total: float,
        return_url: Optional[str], cancel_url: Optional[str], notify_url: Optional[str] = None
) -> dict[str, Any]:
    exp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 15*60))
    if channel == PaymentChannel.REDIRECT.value:
        return {
            "order_id": oid,
            "pay_url": f"{CHECKOUT_URL}/{oid}",
            "expires_at": exp,
            "notify_url": notify_url
        }
    return {
        "order_id": oid,
        "qr_code_url": f"{QR_URL}/{oid}.png",
        "expires_at": exp,
        "notify_url": notify_url
    }


async def _stub_paygate_query(order_id: int) -> dict[str, Any]:
    return {
        "order_id": order_id,
        "status": "paid",
        "transaction_id": f"VNP{order_id}_{int(time.time())}",
        "paid_amount": None,
        "gateway_response_code": "00"
    }


async def create_order(payload: dict[str, Any]) -> str:
    """
    Create a payment order and save to database.
    Args:
      payload: {
        "context_id": "ctx_123",
        "product_sku": "SKU001",
        "quantity": 1,
        "channel": "redirect|qr"
      }
    Returns: PaymentResponse with order_id, context_id, and next_action

    Note: context_id, return_url, cancel_url, and notify_url are auto-generated
    by Payment Agent. Salesperson uses returned context_id for later queries.
    """
    session = db_connection.get_session()
    try:
        context_id = payload.get("context_id")
        product_sku = payload.get("product_sku")
        quantity = payload.get("quantity")
        channel = payload.get("channel")

        # Check payload parameters
        if not context_id:
            # Return ResponseFormat(status=Status.CTX_ID_NOT_FOUND).to_json()
            pass

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

        order_id = str(order.id)
        return_url = f"{CALLBACK_SERVICE_URL}/return/vnpay?order_id={order_id}"
        cancel_url = f"{CALLBACK_SERVICE_URL}/cancel/vnpay?order_id={order_id}"
        notify_url = f"{CALLBACK_SERVICE_URL}/callback/vnpay?order_id={order_id}"

        paygate_response = await _stub_paygate_create(
            channel, order.id, total_amount,
            return_url, cancel_url, notify_url
        )

        # Build next_action
        if channel == PaymentChannel.REDIRECT:
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
            context_id=context_id,
            status=PaymentStatus.PENDING,
            provider_name=PAYGATE_PROVIDER,
            order_id=order_id,
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

        try:
            order_id_int = int(order_id)
        except (TypeError, ValueError):
            return ResponseFormat(
                status=Status.INVALID_PARAMS,
                message=f"Invalid order_id format: {order_id}. Must be an integer."
            ).to_json()

        order = session.query(Order).filter(Order.id == order_id_int).first()

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


async def query_gateway_status(payload: dict[str, Any]) -> str:
    """
    Query payment gateway for actual order status and update order in database.
    This is called by Payment Agent after receiving callback notification from Redis.

    Flow:
    1. Query payment gateway for actual status
    2. Update order status in database based on gateway response

    Args:
      payload: {"order_id": "123"}
    Returns: Gateway response with actual payment status and updated order
    """
    session = db_connection.get_session()
    try:
        order_id = payload.get("order_id")

        try:
            order_id_int = int(order_id)
        except (TypeError, ValueError):
            return ResponseFormat(
                status=Status.INVALID_PARAMS,
                message=f"Invalid order_id format: {order_id}. Must be an integer."
            ).to_json()

        # Step 1: Query payment gateway (stub)
        gateway_response = await _stub_paygate_query(order_id_int)
        actual_status = gateway_response.get("status", "failed")

        # Step 2: Update order status in database
        order = session.query(Order).filter(Order.id == order_id_int).first()
        if not order:
            return ResponseFormat(status=Status.ORDER_NOT_FOUND, message="Order not found").to_json()

        try:
            order.status = OrderStatus(actual_status)
        except ValueError:
            valid_statuses = [s.value for s in OrderStatus]
            return ResponseFormat(
                status=Status.INVALID_PARAMS,
                message=f"Invalid status from gateway: {actual_status}. Must be one of: {', '.join(valid_statuses)}"
            ).to_json()

        session.commit()
        session.refresh(order)

        return ResponseFormat(data={
            "gateway_response": gateway_response,
            "order": order.to_dict()
        }).to_json()
    except Exception as e:
        session.rollback()
        return ResponseFormat(status=Status.UNKNOWN_ERROR, message=str(e)).to_json()
    finally:
        session.close()


payment_mcp_logger.info("Initializing ADK tool for payment...")
create_order_tool = FunctionTool(create_order)
query_order_status_tool = FunctionTool(query_order_status)
query_gateway_status_tool = FunctionTool(query_gateway_status)

ADK_TOOLS_FOR_PAYMENT = {
    create_order_tool.name: create_order_tool,
    query_order_status_tool.name: query_order_status_tool,
    query_gateway_status_tool.name: query_gateway_status_tool,
}

for adk_tool in ADK_TOOLS_FOR_PAYMENT.values():
    payment_mcp_logger.info(f"ADK tool '{adk_tool.name}' initialized and ready to be exposed via MCP.")