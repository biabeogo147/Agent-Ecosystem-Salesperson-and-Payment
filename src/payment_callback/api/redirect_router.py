import asyncio
from pathlib import Path

from fastapi import APIRouter, Query
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from payment_callback import callback_logger
from payment_callback.services import publish_payment_callback

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
redirect_router = APIRouter(tags=["Payment Redirect"])


@redirect_router.get("/checkout/{order_id}", response_class=HTMLResponse)
async def checkout_page(request: Request, order_id: int):
    """
    Stub checkout page for testing payment flow.

    This endpoint simulates a payment gateway checkout page with:
    - "Continue Payment" button -> redirects to return URL (success)
    - "Cancel" button -> redirects to cancel URL

    Args:
        request: FastAPI request object
        order_id: Order ID to process
    """
    callback_logger.info(f"Checkout page accessed for order_id={order_id}")

    return_url = f"/return/vnpay?order_id={order_id}"
    cancel_url = f"/cancel/vnpay?order_id={order_id}"

    return templates.TemplateResponse(
        "checkout.html",
        {
            "request": request,
            "order_id": order_id,
            "return_url": return_url,
            "cancel_url": cancel_url
        }
    )


@redirect_router.get("/return/vnpay", response_class=HTMLResponse)
async def vnpay_return(request: Request, order_id: int = Query(..., description="Order ID")):
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
        asyncio.create_task(publish_payment_callback(order_id))

        return templates.TemplateResponse(
            "success.html",
            {"request": request, "order_id": order_id}
        )

    except Exception as e:
        callback_logger.error(f"Failed to process return redirect: {e}")
        return templates.TemplateResponse(
            "success.html",
            {"request": request, "order_id": order_id}
        )


@redirect_router.get("/cancel/vnpay", response_class=HTMLResponse)
async def vnpay_cancel(request: Request, order_id: int = Query(..., description="Order ID")):
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
        asyncio.create_task(publish_payment_callback(order_id))

        return templates.TemplateResponse(
            "cancel.html",
            {"request": request, "order_id": order_id}
        )

    except Exception as e:
        callback_logger.error(f"Failed to process cancel redirect: {e}")
        return templates.TemplateResponse(
            "cancel.html",
            {"request": request, "order_id": order_id}
        )
