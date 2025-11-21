from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.utils.response_format import ResponseFormat
from src.utils.status import Status
from src.web_hook.api import product_router, document_router

app = FastAPI(
    title="Provider Webhook API",
    description="API for providers to manage products and documents",
    version="1.0.0"
)

# Include routers
app.include_router(product_router)
app.include_router(document_router)


if __name__ == "__main__":
    import uvicorn
    from src.config import WEBHOOK_HOST, WEBHOOK_PORT
    uvicorn.run(app, host=WEBHOOK_HOST, port=WEBHOOK_PORT)