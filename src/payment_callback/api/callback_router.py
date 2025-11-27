import asyncio
from pathlib import Path
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from src.payment_callback import callback_logger
from src.payment_callback.services.redis_publisher import publish_payment_callback
from src.utils.response_format import ResponseFormat
from src.utils.status import Status

# Setup Jinja2 templates
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

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


@redirect_router.get("/return/vnpay", response_class=HTMLResponse)
async def vnpay_return(request: Request, order_id: str = Query(..., description="Order ID")):
    """
    Handle successful payment redirect from VNPay.

    This endpoint is called when VNPay redirects the user back after
    successful payment. It:
    1. Publishes callback to Redis for Payment Agent to process
    2. Renders success page to user

    Args:
        request: FastAPI request object
        order_id: Order ID from our system
    """
    callback_logger.info(f"Received return redirect for order_id={order_id}")

    try:
        # Publish to Redis for Payment Agent to query actual status
        asyncio.create_task(publish_payment_callback(order_id))

        # Render success template
        return templates.TemplateResponse(
            "success.html",
            {"request": request, "order_id": order_id}
        )

    except Exception as e:
        callback_logger.error(f"Failed to process return redirect: {e}")
        # On error, still render success page (Payment Agent will verify actual status)
        return templates.TemplateResponse(
            "success.html",
            {"request": request, "order_id": order_id}
        )


@redirect_router.get("/cancel/vnpay", response_class=HTMLResponse)
async def vnpay_cancel(request: Request, order_id: str = Query(..., description="Order ID")):
    """
    Handle cancelled payment redirect from VNPay.

    This endpoint is called when VNPay redirects the user back after
    they cancel the payment. It:
    1. Publishes callback to Redis for Payment Agent to process
    2. Renders cancel page to user

    Args:
        request: FastAPI request object
        order_id: Order ID from our system
    """
    callback_logger.info(f"Received cancel redirect for order_id={order_id}")

    try:
        # Publish to Redis for Payment Agent to query actual status
        asyncio.create_task(publish_payment_callback(order_id))

        # Render cancel template
        return templates.TemplateResponse(
            "cancel.html",
            {"request": request, "order_id": order_id}
        )

    except Exception as e:
        callback_logger.error(f"Failed to process cancel redirect: {e}")
        # On error, still render cancel page (Payment Agent will verify actual status)
        return templates.TemplateResponse(
            "cancel.html",
            {"request": request, "order_id": order_id}
        )