"""
WebSocket connection manager for handling multiple client connections.

Manages connections grouped by context_id, allowing targeted message delivery
to specific conversations.
"""
from typing import Any

from fastapi import WebSocket

from src.websocket_server import ws_server_logger as logger


class ConnectionManager:
    """
    Manages WebSocket connections grouped by context_id.

    Each context_id can have multiple connections (e.g., multiple tabs/devices).
    Messages are broadcast to all connections within a context_id.
    """

    def __init__(self):
        # context_id -> list of WebSocket connections
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, context_id: str) -> None:
        """
        Accept a new WebSocket connection and register it.

        Args:
            websocket: The WebSocket connection to register
            context_id: The context/conversation ID to associate with
        """
        await websocket.accept()

        if context_id not in self.active_connections:
            self.active_connections[context_id] = []

        self.active_connections[context_id].append(websocket)
        logger.info(
            f"WebSocket connected: context_id={context_id}, "
            f"total_connections={len(self.active_connections[context_id])}"
        )

    def disconnect(self, websocket: WebSocket, context_id: str) -> None:
        """
        Remove a WebSocket connection from the registry.

        Args:
            websocket: The WebSocket connection to remove
            context_id: The context/conversation ID it was associated with
        """
        if context_id in self.active_connections:
            try:
                self.active_connections[context_id].remove(websocket)
                logger.info(
                    f"WebSocket disconnected: context_id={context_id}, "
                    f"remaining={len(self.active_connections[context_id])}"
                )

                # Clean up empty context entries
                if not self.active_connections[context_id]:
                    del self.active_connections[context_id]
                    logger.debug(f"Removed empty context: {context_id}")

            except ValueError:
                logger.warning(f"WebSocket not found in context: {context_id}")

    async def send_to_context(self, context_id: str, message: dict[str, Any]) -> int:
        """
        Send a message to all connections in a specific context.

        Args:
            context_id: The context/conversation ID to send to
            message: The message dict to send (will be JSON serialized)

        Returns:
            Number of connections the message was sent to
        """
        sent_count = 0

        if context_id not in self.active_connections:
            logger.debug(f"No active connections for context: {context_id}")
            return sent_count

        connections = self.active_connections[context_id].copy()
        disconnected = []

        for connection in connections:
            try:
                await connection.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send to connection: {e}")
                disconnected.append(connection)

        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn, context_id)

        if sent_count > 0:
            logger.info(
                f"Sent message to {sent_count} connection(s) in context: {context_id}"
            )

        return sent_count

    async def broadcast_all(self, message: dict[str, Any]) -> int:
        """
        Broadcast a message to all connected clients across all contexts.

        Args:
            message: The message dict to send

        Returns:
            Total number of connections the message was sent to
        """
        total_sent = 0

        for context_id in list(self.active_connections.keys()):
            sent = await self.send_to_context(context_id, message)
            total_sent += sent

        return total_sent

    def get_connection_count(self, context_id: str | None = None) -> int:
        """
        Get the number of active connections.

        Args:
            context_id: If provided, return count for specific context.
                       If None, return total across all contexts.

        Returns:
            Number of active connections
        """
        if context_id:
            return len(self.active_connections.get(context_id, []))

        return sum(len(conns) for conns in self.active_connections.values())

    def get_active_contexts(self) -> list[str]:
        """
        Get list of context IDs with active connections.

        Returns:
            List of context IDs
        """
        return list(self.active_connections.keys())


# Singleton instance
manager = ConnectionManager()
