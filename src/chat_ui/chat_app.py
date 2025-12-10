from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from chat_ui.schemas import LoginRequest
from src.chat_ui import chat_ui_logger as logger
from src.config import CHAT_UI_HOST, CHAT_UI_PORT, API_GATEWAY_PORT

API_GATEWAY_URL = f"http://localhost:{API_GATEWAY_PORT}"

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Salesperson Chat UI",
    description="Chat interface - WebSocket only communication",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def serve_index():
    """Serve the main chat page."""
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)


@app.get("/login")
async def serve_login():
    """Serve the login page."""
    login_path = STATIC_DIR / "login.html"
    if not login_path.exists():
        raise HTTPException(status_code=404, detail="login.html not found")
    return FileResponse(login_path)


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.post("/api/login")
async def proxy_login(request: LoginRequest):
    """Proxy login request to API Gateway."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_GATEWAY_URL}/auth/login",
                json=request.model_dump(),
                timeout=10.0
            )
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Login proxy error: {e}")
        raise HTTPException(status_code=503, detail="API Gateway unavailable")


@app.get("/api/conversations")
async def proxy_conversations(
    limit: int = Query(default=20, le=50, ge=1),
    authorization: Optional[str] = Header(default=None)
):
    """Proxy conversations list request to API Gateway."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_GATEWAY_URL}/auth/conversations",
                params={"limit": limit},
                headers={"Authorization": authorization},
                timeout=10.0
            )
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Conversations proxy error: {e}")
        raise HTTPException(status_code=503, detail="API Gateway unavailable")


@app.get("/api/conversations/{conversation_id}/messages")
async def proxy_conversation_messages(
    conversation_id: int,
    limit: int = Query(default=50, le=100, ge=1),
    authorization: Optional[str] = Header(default=None)
):
    """Proxy conversation messages request to API Gateway."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_GATEWAY_URL}/auth/conversations/{conversation_id}/messages",
                params={"limit": limit},
                headers={"Authorization": authorization},
                timeout=10.0
            )

            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Conversation not found")

            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Messages proxy error: {e}")
        raise HTTPException(status_code=503, detail="API Gateway unavailable")


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting Chat UI on http://{CHAT_UI_HOST}:{CHAT_UI_PORT}")
    logger.info(f"API Gateway: ws://localhost:{API_GATEWAY_PORT}")

    uvicorn.run(app, host=CHAT_UI_HOST, port=CHAT_UI_PORT)
