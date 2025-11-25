"""
Payment Callback Service - Receives callbacks from payment gateways.

This service:
1. Receives IPN (Instant Payment Notification) from VNPay
2. Verifies the callback signature
3. Publishes the callback data to Redis for Payment Agent to process

Run with: python -m src.payment_callback.callback_app
"""
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import CALLBACK_SERVICE_HOST, CALLBACK_SERVICE_PORT
from src.payment_callback import callback_logger
from src.payment_callback.api.callback_router import router as callback_router
from src.utils.logger import set_app_context, AppLogger


class AppContextMiddleware(BaseHTTPMiddleware):
    """Middleware to set app logger context for all requests."""

    async def dispatch(self, request, call_next):
        with set_app_context(AppLogger.PAYMENT_CALLBACK):
            response = await call_next(request)
        return response


app = FastAPI(
    title="Payment Callback Service",
    description="Receives payment gateway callbacks (IPN) and publishes to Redis",
    version="1.0.0"
)

# Add context middleware
app.add_middleware(AppContextMiddleware)

# Include routers
app.include_router(callback_router)


@app.on_event("startup")
async def startup_event():
    callback_logger.info(
        f"Payment Callback Service starting on {CALLBACK_SERVICE_HOST}:{CALLBACK_SERVICE_PORT}"
    )


@app.on_event("shutdown")
async def shutdown_event():
    callback_logger.info("Payment Callback Service shutting down")


if __name__ == "__main__":
    import uvicorn

    callback_logger.info(
        f"Starting Payment Callback Service on {CALLBACK_SERVICE_HOST}:{CALLBACK_SERVICE_PORT}"
    )
    uvicorn.run(app, host=CALLBACK_SERVICE_HOST, port=CALLBACK_SERVICE_PORT)
