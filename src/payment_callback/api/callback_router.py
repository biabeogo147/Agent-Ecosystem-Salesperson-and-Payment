import asyncio
import os
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, RedirectResponse

from src.payment_callback import callback_logger
from src.payment_callback.services.redis_publisher import publish_payment_callback
from src.utils.response_format import ResponseFormat
from src.utils.status import Status

# Frontend URL for redirecting users after payment
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

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


# Create a separate router for return/cancel endpoints (no prefix)
redirect_router = APIRouter(tags=["Payment Redirect"])


@redirect_router.get("/return/vnpay")
async def vnpay_return(order_id: str = Query(..., description="Order ID")):
    """
    Handle successful payment redirect from VNPay.

    This endpoint is called when VNPay redirects the user back after
    successful payment. It:
    1. Publishes callback to Redis for Payment Agent to process
    2. Redirects user to frontend success page

    Args:
        order_id: Order ID from our system
    """
    callback_logger.info(f"Received return redirect for order_id={order_id}")

    try:
        # Publish to Redis for Payment Agent to query actual status
        asyncio.create_task(publish_payment_callback(order_id))

        # Redirect user to frontend success page
        redirect_url = f"{FRONTEND_URL}/payment/success?order_id={order_id}"
        callback_logger.info(f"Redirecting user to: {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=302)

    except Exception as e:
        callback_logger.error(f"Failed to process return redirect: {e}")
        # On error, still redirect to frontend but with error param
        error_url = f"{FRONTEND_URL}/payment/error?order_id={order_id}&error={str(e)}"
        return RedirectResponse(url=error_url, status_code=302)


@redirect_router.get("/cancel/vnpay")
async def vnpay_cancel(order_id: str = Query(..., description="Order ID")):
    """
    Handle cancelled payment redirect from VNPay.

    This endpoint is called when VNPay redirects the user back after
    they cancel the payment. It:
    1. Publishes callback to Redis for Payment Agent to process
    2. Redirects user to frontend cancel page

    Args:
        order_id: Order ID from our system
    """
    callback_logger.info(f"Received cancel redirect for order_id={order_id}")

    try:
        # Publish to Redis for Payment Agent to query actual status
        asyncio.create_task(publish_payment_callback(order_id))

        # Redirect user to frontend cancel page
        redirect_url = f"{FRONTEND_URL}/payment/cancel?order_id={order_id}"
        callback_logger.info(f"Redirecting user to: {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=302)

    except Exception as e:
        callback_logger.error(f"Failed to process cancel redirect: {e}")
        # On error, still redirect to frontend but with error param
        error_url = f"{FRONTEND_URL}/payment/error?order_id={order_id}&error={str(e)}"
        return RedirectResponse(url=error_url, status_code=302)