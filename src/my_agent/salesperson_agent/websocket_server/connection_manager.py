"""
WebSocket connection manager for handling multiple client connections.

Manages connections grouped by session_id, allowing targeted message delivery
to specific chat sessions.
"""
from typing import Any

from fastapi import WebSocket

from src.my_agent.salesperson_agent.websocket_server import ws_server_logger as logger


class ConnectionManager:
    """
    Manages WebSocket connections grouped by session_id.

    Each session_id can have multiple connections (e.g., multiple tabs/devices).
    Messages are broadcast to all connections within a session_id.
    """

    def __init__(self):
        # session_id -> list of WebSocket connections
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """
        Accept a new WebSocket connection and register it.

        Args:
            websocket: The WebSocket connection to register
            session_id: The chat session ID to associate with
        """
        await websocket.accept()

        if session_id not in self.active_connections:
            self.active_connections[session_id] = []

        self.active_connections[session_id].append(websocket)
        logger.info(
            f"WebSocket connected: session_id={session_id}, "
            f"total_connections={len(self.active_connections[session_id])}"
        )

    def disconnect(self, websocket: WebSocket, session_id: str) -> None:
        """
        Remove a WebSocket connection from the registry.

        Args:
            websocket: The WebSocket connection to remove
            session_id: The chat session ID it was associated with
        """
        if session_id in self.active_connections:
            try:
                self.active_connections[session_id].remove(websocket)
                logger.info(
                    f"WebSocket disconnected: session_id={session_id}, "
                    f"remaining={len(self.active_connections[session_id])}"
                )

                # Clean up empty session entries
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]
                    logger.debug(f"Removed empty session: {session_id}")

            except ValueError:
                logger.warning(f"WebSocket not found in session: {session_id}")

    async def send_to_session(self, session_id: str, message: dict[str, Any]) -> int:
        """
        Send a message to all connections in a specific session.

        Args:
            session_id: The chat session ID to send to
            message: The message dict to send (will be JSON serialized)

        Returns:
            Number of connections the message was sent to
        """
        sent_count = 0

        if session_id not in self.active_connections:
            logger.debug(f"No active connections for session: {session_id}")
            return sent_count

        connections = self.active_connections[session_id].copy()
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
            self.disconnect(conn, session_id)

        if sent_count > 0:
            logger.info(
                f"Sent message to {sent_count} connection(s) in session: {session_id}"
            )

        return sent_count

    def get_connection_count(self, session_id: str | None = None) -> int:
        """
        Get the number of active connections.

        Args:
            session_id: If provided, return count for specific session.
                       If None, return total across all sessions.

        Returns:
            Number of active connections
        """
        if session_id:
            return len(self.active_connections.get(session_id, []))

        return sum(len(conns) for conns in self.active_connections.values())

    def get_active_sessions(self) -> list[str]:
        """
        Get list of session IDs with active connections.

        Returns:
            List of session IDs
        """
        return list(self.active_connections.keys())


# Singleton instance
manager = ConnectionManager()
