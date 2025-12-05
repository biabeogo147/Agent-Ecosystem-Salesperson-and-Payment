from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, Session
from google.genai.types import Content, Part

from src.my_agent.salesperson_agent.agent import root_agent
from src.my_agent.salesperson_agent import salesperson_agent_logger as logger
from src.config import SALESPERSON_AGENT_APP_HOST, SALESPERSON_AGENT_APP_PORT


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
async def lifespan(_: FastAPI):
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


@app.websocket("/agent/stream")
async def agent_stream_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat responses.

    Protocol:
    Client sends: {"type": "chat", "conversation_id": "...", "message": "...", "user_id": 123}
    Server sends: {"type": "complete", "conversation_id": "...", "content": "..."}

    TODO: Implement token-by-token streaming when ADK supports it.
    Currently sends complete response as single message.
    """
    await websocket.accept()
    logger.info("Agent stream client connected")

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "chat":
                conversation_id = data.get("conversation_id")
                message = data.get("message")
                user_id = data.get("user_id")

                if not conversation_id or not message:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Missing conversation_id or message"
                    })
                    continue

                try:
                    if not _session_service:
                        raise RuntimeError("Session service not initialized")

                    # Get or create ADK session using conversation_id
                    session = await _session_service.get_session(conversation_id)
                    if not session:
                        session = Session(id=conversation_id)
                        await _session_service.create_session(session)
                        logger.info(f"Created new ADK session for conversation: {conversation_id}")

                    # Create content
                    user_content = Content(
                        role="user",
                        parts=[Part(text=message)]
                    )

                    logger.info(f"Processing chat for conversation {conversation_id}, user {user_id}")

                    # Run agent
                    runner = Runner(agent=root_agent, session_service=_session_service)
                    result = await runner.run_async(
                        session_id=conversation_id,
                        content=user_content
                    )

                    # Extract response
                    response_text = extract_agent_response(result)

                    # Send complete response
                    # TODO: Implement token streaming when ADK supports it
                    await websocket.send_json({
                        "type": "complete",
                        "conversation_id": conversation_id,
                        "content": response_text
                    })

                    logger.info(f"Response sent for conversation {conversation_id}")
                    
                except Exception as e:
                    logger.error(f"Stream chat error: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
            
            elif data.get("type") == "authenticate":
                username = data.get("username")
                password = data.get("password")
                
                if not username or not password:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Missing username or password"
                    })
                    continue
                
                try:
                    logger.info(f"Processing authentication request for user: {username}")
                    
                    from src.my_agent.salesperson_agent.salesperson_mcp_client import get_salesperson_mcp_client
                    client = get_salesperson_mcp_client()
                    result = await client.authenticate_user(username=username, password=password)
                    
                    if result.get("status") == "00":
                        await websocket.send_json({
                            "type": "authenticate_response",
                            "status": "success",
                            "data": result.get("data")
                        })
                        logger.info(f"Authentication successful for user: {username}")
                    else:
                        await websocket.send_json({
                            "type": "authenticate_response",
                            "status": "failure",
                            "message": result.get("message", "Authentication failed")
                        })
                        logger.warning(f"Authentication failed for user: {username}")
                        
                except Exception as e:
                    logger.error(f"Authentication error: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                    
    except WebSocketDisconnect:
        logger.info("Agent stream client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=SALESPERSON_AGENT_APP_HOST,
        port=SALESPERSON_AGENT_APP_PORT
    )
