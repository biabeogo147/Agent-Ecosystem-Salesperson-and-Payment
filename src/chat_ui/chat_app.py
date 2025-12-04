from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.chat_ui import chat_ui_logger as logger
from src.config import CHAT_UI_HOST, CHAT_UI_PORT, WS_SERVER_PORT

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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


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


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting Chat UI on http://{CHAT_UI_HOST}:{CHAT_UI_PORT}")
    logger.info(f"WebSocket Server: ws://localhost:{WS_SERVER_PORT}")

    uvicorn.run(app, host=CHAT_UI_HOST, port=CHAT_UI_PORT)
