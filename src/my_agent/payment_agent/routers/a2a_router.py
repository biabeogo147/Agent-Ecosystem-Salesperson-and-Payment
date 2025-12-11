"""
A2A Router for Payment Agent.

Exposes the A2A protocol endpoints:
- GET /.well-known/agent-card.json - Agent card discovery
- POST / - JSON-RPC message.send handler
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.my_agent.payment_agent.payment_a2a.payment_a2a_handler import PAYMENT_HANDLER

a2a_router = APIRouter(tags=["A2A"])


@a2a_router.get("/.well-known/agent-card.json")
async def get_agent_card():
    """Return the A2A agent card for this agent."""
    return JSONResponse(content=PAYMENT_HANDLER.get_agent_card())


@a2a_router.post("/")
async def message_send(request: Request):
    """
    Handle A2A message.send JSON-RPC requests.

    This endpoint receives JSON-RPC 2.0 requests with method "message.send"
    and dispatches them to the appropriate skill handler.
    """
    return await PAYMENT_HANDLER.handle_message_send(request)
