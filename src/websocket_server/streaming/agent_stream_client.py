import json
from typing import AsyncIterator

import websockets
from websockets import ClientConnection
from websockets.exceptions import ConnectionClosed
from src.websocket_server import get_ws_server_logger 

logger = get_ws_server_logger()


class AgentStreamClient:
    """
    WebSocket client for streaming communication with Salesperson Agent App.
    
    Usage:
        async with AgentStreamClient(agent_ws_url) as client:
            await client.send({"type": "chat", "session_id": "...", "message": "..."})
            async for msg in client.receive():
                # Process streaming messages
                if msg.get("type") == "complete":
                    break
    """
    
    def __init__(self, agent_ws_url: str):
        """
        Initialize agent stream client.
        
        Args:
            agent_ws_url: WebSocket URL of Salesperson Agent App (e.g., ws://localhost:8086/agent/stream)
        """
        self.agent_ws_url = agent_ws_url
        self.ws: ClientConnection | None = None
    
    async def __aenter__(self):
        """Connect to agent WebSocket."""
        try:
            self.ws = await websockets.connect(
                self.agent_ws_url,
                ping_interval=20,
                ping_timeout=10
            )
            logger.info(f"Connected to Agent App: {self.agent_ws_url}")
            return self
        except Exception as e:
            logger.error(f"Failed to connect to Agent App: {e}")
            raise
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Disconnect from agent WebSocket."""
        if self.ws:
            try:
                await self.ws.close()
                logger.info("Disconnected from Agent App")
            except Exception as e:
                logger.error(f"Error closing Agent App connection: {e}")
    
    async def send(self, message: dict) -> None:
        """
        Send message to agent.
        
        Args:
            message: Message dict to send (will be JSON serialized)
            
        Raises:
            RuntimeError: If not connected
        """
        if not self.ws:
            raise RuntimeError("Not connected to Agent App")
        
        try:
            await self.ws.send(json.dumps(message))
            logger.debug(f"Sent to Agent App: {message.get('type')}")
        except Exception as e:
            logger.error(f"Error sending to Agent App: {e}")
            raise
    
    async def receive(self) -> AsyncIterator[dict]:
        """
        Receive streaming messages from agent.
        
        Yields:
            Dict messages from agent
            
        Raises:
            RuntimeError: If not connected
        """
        if not self.ws:
            raise RuntimeError("Not connected to Agent App")
        
        try:
            while True:
                data = await self.ws.recv()
                
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                
                try:
                    message = json.loads(data)
                    logger.debug(f"Received from Agent App: {message.get('type')}")
                    yield message
                    
                    # Stop if complete or error
                    if message.get("type") in ("complete", "error"):
                        break
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Agent App message: {e}")
                    continue
                    
        except ConnectionClosed:
            logger.info("Agent App connection closed")
        except Exception as e:
            logger.error(f"Error receiving from Agent App: {e}")
            raise
