"""
Custom Chat UI FastAPI Application.

Serves a simple chat interface and proxies requests to the ADK Salesperson Agent.
"""
import uuid
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.chat_ui import chat_ui_logger as logger
from src.config import ADK_AGENT_URL, CHAT_UI_HOST, CHAT_UI_PORT, WS_SERVER_PORT

# Static files directory
STATIC_DIR = Path(__file__).parent / "static"


class ChatRequest(BaseModel):
    """Request model for chat messages."""
    session_id: str
    message: str


class ChatResponse(BaseModel):
    """Response model for chat messages."""
    session_id: str
    message_id: str
    response: str
    raw: dict | None = None


app = FastAPI(
    title="Salesperson Chat UI",
    description="Custom chat interface for Salesperson Agent",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def build_jsonrpc_payload(session_id: str, message: str) -> dict:
    """
    Build JSON-RPC 2.0 payload for ADK agent.

    Args:
        session_id: Chat session ID
        message: User message text

    Returns:
        JSON-RPC 2.0 formatted payload
    """
    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tasks/send",
        "params": {
            "id": session_id,
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": message}]
            }
        }
    }


def extract_agent_response(jsonrpc_response: dict) -> str:
    """
    Extract text response from JSON-RPC response.

    Args:
        jsonrpc_response: Response from ADK agent

    Returns:
        Extracted text response or error message
    """
    try:
        if "error" in jsonrpc_response:
            return f"Error: {jsonrpc_response['error'].get('message', 'Unknown error')}"

        result = jsonrpc_response.get("result", {})

        # Try to extract from artifacts (newer format)
        artifacts = result.get("artifacts", [])
        if artifacts:
            for artifact in artifacts:
                parts = artifact.get("parts", [])
                for part in parts:
                    if part.get("type") == "text":
                        return part.get("text", "")

        # Try to extract from history
        history = result.get("history", [])
        if history:
            # Get the last agent message
            for msg in reversed(history):
                if msg.get("role") == "agent":
                    parts = msg.get("parts", [])
                    for part in parts:
                        if part.get("type") == "text":
                            return part.get("text", "")

        # Try direct result text
        if "text" in result:
            return result["text"]

        return "No response from agent"

    except Exception as e:
        logger.error(f"Failed to extract response: {e}")
        return f"Error extracting response: {str(e)}"


@app.post("/api/chat", response_model=ChatResponse)
async def chat_proxy(request: ChatRequest):
    """
    Proxy chat messages to ADK Salesperson Agent.

    Args:
        request: Chat request with session_id and message

    Returns:
        Agent response
    """
    logger.info(f"Chat request: session_id={request.session_id}, message={request.message[:50]}...")

    try:
        payload = build_jsonrpc_payload(request.session_id, request.message)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                ADK_AGENT_URL,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            jsonrpc_response = response.json()

        agent_text = extract_agent_response(jsonrpc_response)
        logger.info(f"Agent response: {agent_text[:100]}...")

        return ChatResponse(
            session_id=request.session_id,
            message_id=str(uuid.uuid4()),
            response=agent_text,
            raw=jsonrpc_response
        )

    except httpx.TimeoutException:
        logger.error("Request to ADK agent timed out")
        raise HTTPException(status_code=504, detail="Agent request timed out")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from ADK agent: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))

    except Exception as e:
        logger.error(f"Failed to proxy chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config")
async def get_config():
    """
    Return frontend configuration.

    Returns:
        Config including WebSocket server URL
    """
    return {
        "ws_url": f"ws://localhost:{WS_SERVER_PORT}",
        "agent_url": ADK_AGENT_URL
    }


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


# Mount static files (after specific routes)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting Chat UI on http://{CHAT_UI_HOST}:{CHAT_UI_PORT}")
    logger.info(f"ADK Agent URL: {ADK_AGENT_URL}")
    logger.info(f"WebSocket Server: ws://localhost:{WS_SERVER_PORT}")

    uvicorn.run(app, host=CHAT_UI_HOST, port=CHAT_UI_PORT)
