import time
from decimal import Decimal
from typing import Optional, Any

from google.adk.tools import FunctionTool

from src.config import *
from src.data.models.db_entity.order import Order
from src.data.models.db_entity.order_item import OrderItem
from src.data.models.db_entity.product import Product
from src.data.models.enum.order_status import OrderStatus
from src.data.postgres.connection import db_connection
from src.my_agent.my_a2a_common.payment_schemas.next_action import NextAction
from src.my_agent.my_a2a_common.payment_schemas.payment_enums import *
from src.my_agent.my_a2a_common.payment_schemas.payment_response import PaymentResponse
from src.utils.response_format import ResponseFormat
from src.utils.status import Status
from . import payment_mcp_logger


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


async def create_order(
    context_id: str,
    items: list[dict[str, Any]],
    channel: str,
    customer_name: str = "",
    customer_email: str = "",
    customer_phone: str = "",
    customer_shipping_address: str = "",
    note: str = "",
    user_id: Optional[int] = None
) -> str:
    """
    Create a payment order with multiple items and save to database.

    Args:
        context_id: Unique context identifier for the payment session
        items: List of order items, each containing:
            - sku: Product SKU (optional if unit_price provided)
            - name: Product name (optional, will be looked up if sku provided)
            - quantity: Quantity to purchase (required)
            - unit_price: Price per unit (optional, will be looked up from product if sku provided)
            - currency: Currency code (optional, defaults to USD)
        channel: Payment channel, either "redirect" or "qr"
        customer_name: Customer name (optional)
        customer_email: Customer email (optional)
        customer_phone: Customer phone number (optional)
        customer_shipping_address: Shipping address (optional)
        note: Additional notes for the order (optional)
        user_id: User ID associated with the order (optional)

    Returns:
        JSON string containing PaymentResponse with order_id, context_id, and next_action
    """
    session = db_connection.get_session()
    try:
        # Validate required fields
        if not context_id:
            return ResponseFormat(
                status=Status.INVALID_PARAMS,
                message="context_id is required"
            ).to_json()

        if not items:
            return ResponseFormat(
                status=Status.INVALID_PARAMS,
                message="items list is required and cannot be empty"
            ).to_json()

        if not channel:
            return ResponseFormat(
                status=Status.INVALID_PARAMS,
                message="channel is required (redirect or qr)"
            ).to_json()

        order_items = []
        total_amount = Decimal("0")
        currency = "USD"

        for item in items:
            sku = item.get("sku")
            quantity = item.get("quantity", 1)
            unit_price = item.get("unit_price")
            item_currency = item.get("currency", "USD")
            item_name = item.get("name")

            # If unit_price not provided, lookup from product database
            if unit_price is None:
                if not sku:
                    return ResponseFormat(
                        status=Status.INVALID_PARAMS,
                        message="Each item must have either 'sku' or 'unit_price'"
                    ).to_json()
                product = session.query(Product).filter(Product.sku == sku).first()
                if not product:
                    return ResponseFormat(
                        status=Status.PRODUCT_NOT_FOUND,
                        message=f"Product with SKU '{sku}' not found"
                    ).to_json()
                unit_price = float(product.price)
                item_currency = product.currency
                if not item_name:
                    item_name = product.name

            # Validate item data
            if not item_name:
                item_name = sku or "Unknown Product"

            if quantity <= 0:
                return ResponseFormat(
                    status=Status.INVALID_PARAMS,
                    message=f"Invalid quantity for item '{item_name}': must be > 0"
                ).to_json()

            # Create OrderItem (will be added after Order is created)
            order_items.append({
                "product_sku": sku or "CUSTOM",
                "product_name": item_name,
                "quantity": quantity,
                "unit_price": Decimal(str(unit_price)),
                "currency": item_currency
            })

            total_amount += Decimal(str(unit_price)) * quantity
            currency = item_currency  # Use last item's currency (should be consistent)

        # Create Order
        order = Order(
            context_id=context_id,
            user_id=user_id,
            total_amount=total_amount,
            currency=currency,
            status=OrderStatus.PENDING,
            note=note or ""
        )
        session.add(order)
        session.flush()  # Get order.id without committing

        # Create OrderItems
        for item_data in order_items:
            order_item = OrderItem(
                order_id=order.id,
                product_sku=item_data["product_sku"],
                product_name=item_data["product_name"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                currency=item_data["currency"]
            )
            session.add(order_item)

        session.commit()
        session.refresh(order)

        order_id = str(order.id)
        return_url = f"{CALLBACK_SERVICE_URL}/return/vnpay?order_id={order_id}"
        cancel_url = f"{CALLBACK_SERVICE_URL}/cancel/vnpay?order_id={order_id}"
        notify_url = f"{CALLBACK_SERVICE_URL}/callback/vnpay?order_id={order_id}"

        paygate_response = await _stub_paygate_create(
            channel, order.id, float(total_amount),
            return_url, cancel_url, notify_url
        )

        # Build next_action based on channel
        if channel == PaymentChannel.REDIRECT.value or channel == "redirect":
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

        payment_mcp_logger.info(
            f"Order created: order_id={order_id}, context_id={context_id}, "
            f"items={len(order_items)}, total={total_amount} {currency}"
        )

        return ResponseFormat(data=res.model_dump()).to_json()

    except Exception as e:
        session.rollback()
        payment_mcp_logger.exception(
            f"Failed to create order: context_id={context_id}, items_count={len(items) if items else 0}"
        )
        return ResponseFormat(status=Status.UNKNOWN_ERROR, message=str(e)).to_json()
    finally:
        session.close()


async def query_order_status(
    context_id: str,
    order_id: Optional[str] = None
) -> str:
    """
    Query order status from database by context_id and/or order_id.

    Args:
        context_id: Payment context identifier (required)
        order_id: Specific order ID to query (optional). If provided, query specific order.
                  If not provided, query all orders for the context_id.

    Returns:
        JSON string with order status:
        - If order_id provided: Single order with that ID (verified against context_id)
        - If only context_id: All orders for that context_id
    """
    session = db_connection.get_session()
    try:
        if not context_id:
            return ResponseFormat(
                status=Status.INVALID_PARAMS,
                message="context_id is required"
            ).to_json()

        if order_id:
            # Query specific order by order_id, verify it belongs to context_id
            try:
                order_id_int = int(order_id)
            except (TypeError, ValueError):
                return ResponseFormat(
                    status=Status.INVALID_PARAMS,
                    message=f"Invalid order_id format: {order_id}. Must be an integer."
                ).to_json()

            order = session.query(Order).filter(
                Order.id == order_id_int,
                Order.context_id == context_id
            ).first()

            if not order:
                return ResponseFormat(
                    status=Status.ORDER_NOT_FOUND,
                    message=f"Order {order_id} not found for context_id {context_id}"
                ).to_json()

            res = PaymentResponse(
                context_id=order.context_id,
                status=_map_order_status_to_payment_status(order.status),
                order_id=str(order.id),
            )
            return ResponseFormat(data={**res.model_dump(), "order": order.to_dict()}).to_json()

        else:
            # Query all orders for context_id
            orders = session.query(Order).filter(Order.context_id == context_id).all()

            if not orders:
                return ResponseFormat(
                    status=Status.ORDER_NOT_FOUND,
                    message=f"No orders found for context_id {context_id}"
                ).to_json()

            # Return list of orders
            orders_data = [order.to_dict() for order in orders]

            # For backward compatibility, also return PaymentResponse for the first/latest order
            latest_order = orders[-1]
            res = PaymentResponse(
                context_id=context_id,
                status=_map_order_status_to_payment_status(latest_order.status),
                order_id=str(latest_order.id),
            )

            return ResponseFormat(data={
                **res.model_dump(),
                "orders": orders_data,
                "total_orders": len(orders)
            }).to_json()

    except Exception as e:
        payment_mcp_logger.exception(f"Failed to query order status: context_id={context_id}, order_id={order_id}")
        return ResponseFormat(status=Status.UNKNOWN_ERROR, message=str(e)).to_json()
    finally:
        session.close()


async def query_gateway_status(order_id: str) -> str:
    """
    Query payment gateway for actual order status and update order in database.
    This is called by Payment Agent after receiving callback notification from Redis.

    Flow:
    1. Query payment gateway for actual status
    2. Update order status in database based on gateway response

    Args:
        order_id: The order ID to query

    Returns:
        JSON string with gateway response and updated order information
    """
    session = db_connection.get_session()
    try:
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
        payment_mcp_logger.exception(f"Failed to query gateway status: order_id={order_id}")
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