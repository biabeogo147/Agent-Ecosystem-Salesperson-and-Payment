from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from src.web_hook.api import product_router, document_router
from src.utils.logger import set_app_context, AppLogger


class AppContextMiddleware(BaseHTTPMiddleware):
    """Middleware to set app logger context for all requests."""

    async def dispatch(self, request, call_next):
        with set_app_context(AppLogger.WEBHOOK):
            response = await call_next(request)
        return response


app = FastAPI(
    title="Provider Webhook API",
    description="API for providers to manage products and documents",
    version="1.0.0"
)

# Add context middleware
app.add_middleware(AppContextMiddleware)

# Include routers
app.include_router(product_router)
app.include_router(document_router)


if __name__ == "__main__":
    import uvicorn
    from src.config import WEBHOOK_HOST, WEBHOOK_PORT
    uvicorn.run(app, host=WEBHOOK_HOST, port=WEBHOOK_PORT)