from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, Session
from google.adk.models import Content, Part

from src.my_agent.salesperson_agent.agent import root_agent
from src.my_agent.salesperson_agent import salesperson_agent_logger as logger
from src.config import SALESPERSON_AGENT_APP_HOST, SALESPERSON_AGENT_APP_PORT


# Request/Response models
class ChatRequest(BaseModel):
    """Request model for chat messages."""
    session_id: str
    message: str
    user_id: int  # For context and logging


class ChatResponse(BaseModel):
    """Response model for chat messages."""
    session_id: str
    response: str


# Global state
_session_service: InMemorySessionService | None = None
_subscriber_task: asyncio.Task | None = None


def extract_agent_response(result) -> str:
    """
    Extract text response from agent execution result.
    
    Args:
        result: Output from Runner.run_async
        
    Returns:
        Agent's text response
    """
    try:
        # Extract from result based on ADK response structure
        if hasattr(result, 'content') and result.content:
            for part in result.content.parts:
                if hasattr(part, 'text'):
                    return part.text
        
        # Try to get from history if available
        if hasattr(result, 'history') and result.history:
            for msg in reversed(result.history):
                if hasattr(msg, 'role') and msg.role == 'agent':
                    if hasattr(msg, 'parts'):
                        for part in msg.parts:
                            if hasattr(part, 'text'):
                                return part.text
        
        # Fallback
        return "Agent response unavailable"
        
    except Exception as e:
        logger.error(f"Failed to extract response: {e}")
        return f"Error extracting response: {str(e)}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Startup:
    - Initializes session service for agent conversations
    - Starts notification subscriber (moved from WebSocket Server)
    
    Shutdown:
    - Stops notification subscriber
    """
    global _session_service, _subscriber_task
    
    logger.info(f"Salesperson Agent App starting on {SALESPERSON_AGENT_APP_HOST}:{SALESPERSON_AGENT_APP_PORT}")
    
    # Initialize session service
    _session_service = InMemorySessionService()
    logger.info("Session service initialized")
    
    # Start notification subscriber
    from src.my_agent.salesperson_agent.salesperson_notification_subscriber import (
        start_subscriber_background,
        stop_subscriber
    )
    _subscriber_task = start_subscriber_background()
    logger.info("Notification subscriber started")
    
    yield
    
    # Shutdown
    logger.info("Salesperson Agent App shutting down...")
    await stop_subscriber()
    logger.info("Notification subscriber stopped")


app = FastAPI(
    title="Salesperson Agent App",
    description="Internal API for WebSocket Server to interact with ADK Salesperson Agent",
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/chat", response_model=ChatResponse)
async def handle_chat(request: ChatRequest) -> ChatResponse:
    """
    Handle chat message from WebSocket Server.
    
    Flow:
    1. Get or create session from session_service
    2. Create Content from user message
    3. Use Runner.run_async to invoke agent
    4. Extract response from agent output
    5. Return formatted response
    
    Args:
        request: Chat request with session_id, message, and user_id
        
    Returns:
        Chat response with agent's reply
    """
    try:
        if not _session_service:
            raise HTTPException(status_code=500, detail="Session service not initialized")
        
        # Get or create session
        session = await _session_service.get_session(request.session_id)
        if not session:
            session = Session(id=request.session_id)
            await _session_service.create_session(session)
            logger.info(f"Created new session: {request.session_id}")
        
        # Create content from user message
        user_content = Content(
            role="user",
            parts=[Part(text=request.message)]
        )
        
        logger.info(f"Processing chat for session {request.session_id}, user {request.user_id}")
        
        # Run agent
        runner = Runner(agent=root_agent, session_service=_session_service)
        result = await runner.run_async(
            session_id=request.session_id,
            content=user_content
        )
        
        # Extract response
        agent_response = extract_agent_response(result)
        logger.info(f"Agent response generated for session {request.session_id}")
        
        return ChatResponse(
            session_id=request.session_id,
            response=agent_response
        )
        
    except Exception as e:
        logger.error(f"Chat error for session {request.session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/agent/stream")
async def agent_stream_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat responses.
    
    Protocol:
    Client sends: {"type": "chat", "session_id": "...", "message": "...", "user_id": 123}
    Server sends: {"type": "complete", "session_id": "...", "content": "..."}
    
    TODO: Implement token-by-token streaming when ADK supports it.
    Currently sends complete response as single message.
    """
    await websocket.accept()
    logger.info("Agent stream client connected")
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "chat":
                session_id = data.get("session_id")
                message = data.get("message")
                user_id = data.get("user_id")
                
                if not session_id or not message:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Missing session_id or message"
                    })
                    continue
                
                try:
                    if not _session_service:
                        raise RuntimeError("Session service not initialized")
                    
                    # Get or create session
                    session = await _session_service.get_session(session_id)
                    if not session:
                        session = Session(id=session_id)
                        await _session_service.create_session(session)
                        logger.info(f"Created new session: {session_id}")
                    
                    # Create content
                    user_content = Content(
                        role="user",
                        parts=[Part(text=message)]
                    )
                    
                    logger.info(f"Processing stream chat for session {session_id}, user {user_id}")
                    
                    # Run agent
                    runner = Runner(agent=root_agent, session_service=_session_service)
                    result = await runner.run_async(
                        session_id=session_id,
                        content=user_content
                    )
                    
                    # Extract response
                    response_text = extract_agent_response(result)
                    
                    # Send complete response
                    # TODO: Implement token streaming when ADK supports it
                    await websocket.send_json({
                        "type": "complete",
                        "session_id": session_id,
                        "content": response_text
                    })
                    
                    logger.info(f"Stream response sent for session {session_id}")
                    
                except Exception as e:
                    logger.error(f"Stream chat error: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                    
    except WebSocketDisconnect:
        logger.info("Agent stream client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "salesperson_agent_app",
        "session_service": "initialized" if _session_service else "not_initialized"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=SALESPERSON_AGENT_APP_HOST,
        port=SALESPERSON_AGENT_APP_PORT
    )
