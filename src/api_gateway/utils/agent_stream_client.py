import json
from typing import AsyncIterator

import websockets
from websockets import ClientConnection
from websockets.exceptions import ConnectionClosed
from src.api_gateway import get_api_gateway_logger

logger = get_api_gateway_logger()


class AgentStreamClient:
    """
    Persistent WebSocket client for communication with Salesperson Agent App.

    Usage:
        client = AgentStreamClient(agent_ws_url)
        await client.connect()

        # Reuse for multiple messages
        async for msg in client.send_and_receive({"type": "chat", ...}):
            if msg.get("type") == "complete":
                break

        # When done
        await client.disconnect()
    """

    def __init__(self, agent_ws_url: str):
        """
        Initialize agent stream client.

        Args:
            agent_ws_url: WebSocket URL of Salesperson Agent App
        """
        self.agent_ws_url = agent_ws_url
        self.ws: ClientConnection | None = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to Agent App."""
        return self._connected and self.ws is not None

    async def connect(self) -> None:
        """Connect to agent WebSocket."""
        if self.is_connected:
            return

        try:
            self.ws = await websockets.connect(
                self.agent_ws_url,
                ping_interval=20,
                ping_timeout=10
            )
            self._connected = True
            logger.info(f"Connected to Agent App: {self.agent_ws_url}")
        except Exception as e:
            self._connected = False
            logger.error(f"Failed to connect to Agent App: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from agent WebSocket."""
        if self.ws:
            try:
                await self.ws.close()
                logger.info("Disconnected from Agent App")
            except Exception as e:
                logger.error(f"Error closing Agent App connection: {e}")
            finally:
                self.ws = None
                self._connected = False

    async def ensure_connected(self) -> None:
        """Ensure connection is active, reconnect if needed."""
        if not self.is_connected:
            await self.connect()

    async def send_and_receive(self, message: dict) -> AsyncIterator[dict]:
        """
        Send message and yield responses until complete.

        Keeps connection open after receiving complete/error.

        Args:
            message: Message dict to send

        Yields:
            Response messages from agent
        """
        await self.ensure_connected()

        try:
            await self.ws.send(json.dumps(message))
            logger.debug(f"Sent to Agent App: {message.get('type')}")

            while True:
                data = await self.ws.recv()

                if isinstance(data, bytes):
                    data = data.decode("utf-8")

                try:
                    msg = json.loads(data)
                    logger.debug(f"Received from Agent App: {msg.get('type')}")
                    yield msg

                    # Stop receiving but keep connection open
                    if msg.get("type") in ("complete", "error"):
                        break

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Agent App message: {e}")
                    continue

        except ConnectionClosed:
            logger.warning("Agent App connection closed unexpectedly")
            self._connected = False
            self.ws = None
            raise
        except Exception as e:
            logger.error(f"Error in send_and_receive: {e}")
            self._connected = False
            raise
