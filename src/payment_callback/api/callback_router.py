from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.payment_callback import callback_logger
from src.payment_callback.services.redis_publisher import publish_payment_callback

router = APIRouter(prefix="/callback", tags=["Payment Callback"])


@router.get("/vnpay")
async def vnpay_callback(order_id: str = Query(..., description="Order ID")):
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

    # Publish to Redis
    success = await publish_payment_callback(order_id)

    if success:
        return JSONResponse(content={"RspCode": "00", "Message": "Confirm Success"})
    else:
        return JSONResponse(
            content={"RspCode": "99", "Message": "Internal Error"},
            status_code=500
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "payment-callback"}
