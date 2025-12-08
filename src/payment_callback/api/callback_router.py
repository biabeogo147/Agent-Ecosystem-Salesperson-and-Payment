import asyncio
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.payment_callback import callback_logger
from src.payment_callback.services.redis_publisher import publish_payment_callback
from src.utils.response_format import ResponseFormat
from src.utils.status import Status

callback_router = APIRouter(prefix="/callback", tags=["Payment Callback"])


@callback_router.get("/vnpay")
async def vnpay_callback(order_id: int = Query(..., description="Order ID")):
    """
    Handle VNPay callback notification.

    Simple endpoint that:
    1. Receives order_id from payment gateway
    2. Publishes to Redis for Payment Agent to process
    3. Payment Agent will query gateway for actual status

    Args:
        order_id: Order ID from our system
    """
    callback_logger.info(f"Received callback for order_id={order_id}")

    try:
        asyncio.create_task(publish_payment_callback(order_id))
        return JSONResponse(
            content=ResponseFormat(
                status=Status.SUCCESS,
                message="Callback received",
                data={"order_id": order_id}
            ).to_dict()
        )
    except Exception as e:
        callback_logger.error(f"Failed to process callback: {e}")
        return JSONResponse(
            status_code=500,
            content=ResponseFormat(
                status=Status.UNKNOWN_ERROR,
                message=str(e),
                data=None
            ).to_dict()
        )