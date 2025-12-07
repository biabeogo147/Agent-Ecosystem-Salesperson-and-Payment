"""
WebSocket connection manager for handling multiple client connections.

Manages connections grouped by session_id, allowing targeted message delivery
to specific chat sessions. Integrates with Redis for multi-session broadcasting
based on (user_id, conversation_id) mapping.
"""
import asyncio
from typing import Any, Optional

from fastapi import WebSocket

from src.data.redis.cache_keys import CacheKeys, TTL
from src.data.redis.connection import redis_connection
from src.websocket_server import get_ws_server_logger


class ConnectionManager:
    """
    Manages WebSocket connections grouped by session_id.

    Each session_id can have multiple connections (e.g., multiple tabs/devices).
    Messages are broadcast to all connections within a session_id.

    Additionally tracks user_id and conversation_id per session for multi-device
    notification broadcasting via Redis.
    """

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
        # Track metadata per session: {session_id: {user_id, conversation_id}}
        self.session_metadata: dict[str, dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """
        Accept a new WebSocket connection and register it.

        Args:
            websocket: The WebSocket connection to register
            session_id: The chat session ID to associate with
        """
        logger = get_ws_server_logger()

        await websocket.accept()

        if session_id not in self.active_connections:
            self.active_connections[session_id] = []

        self.active_connections[session_id].append(websocket)
        logger.info(
            f"WebSocket connected: session_id={session_id}, "
            f"total_connections={len(self.active_connections[session_id])}"
        )

    async def register_session(
        self,
        session_id: str,
        user_id: int,
        conversation_id: int,
    ) -> None:
        """
        Register session metadata and add to Redis set for multi-session lookup.

        Args:
            session_id: The WebSocket session ID
            user_id: The authenticated user's ID
            conversation_id: The conversation ID this session is viewing
        """
        logger = get_ws_server_logger()

        # Store metadata locally
        self.session_metadata[session_id] = {
            "user_id": user_id,
            "conversation_id": conversation_id
        }

        # Add to Redis set for multi-session lookup
        try:
            redis = await redis_connection.get_client()
            key = CacheKeys.ws_user_conversation_sessions(user_id, conversation_id)
            await redis.sadd(key, session_id)
            await redis.expire(key, TTL.WS_SESSION)

            logger.info(
                f"Registered session in Redis: session_id={session_id}, "
                f"user_id={user_id}, conversation_id={conversation_id}"
            )
        except Exception as e:
            logger.error(f"Failed to register session in Redis: {e}")

    async def unregister_session(self, session_id: str) -> None:
        """
        Remove session from Redis set and cleanup metadata.

        Args:
            session_id: The WebSocket session ID to unregister
        """
        logger = get_ws_server_logger()

        metadata = self.session_metadata.pop(session_id, None)
        if metadata:
            try:
                redis = await redis_connection.get_client()
                key = CacheKeys.ws_user_conversation_sessions(
                    metadata["user_id"],
                    metadata["conversation_id"]
                )
                await redis.srem(key, session_id)

                # Cleanup empty set
                if await redis.scard(key) == 0:
                    await redis.delete(key)

                logger.info(
                    f"Unregistered session from Redis: session_id={session_id}, "
                    f"user_id={metadata['user_id']}, conversation_id={metadata['conversation_id']}"
                )
            except Exception as e:
                logger.error(f"Failed to unregister session from Redis: {e}")

    def disconnect(self, websocket: WebSocket, session_id: str) -> None:
        """
        Remove a WebSocket connection from the registry.

        Args:
            websocket: The WebSocket connection to remove
            session_id: The chat session ID it was associated with
        """
        logger = get_ws_server_logger()

        if session_id in self.active_connections:
            try:
                self.active_connections[session_id].remove(websocket)
                logger.info(
                    f"WebSocket disconnected: session_id={session_id}, "
                    f"remaining={len(self.active_connections[session_id])}"
                )

                # Clean up empty session entries and unregister from Redis
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]
                    logger.debug(f"Removed empty session: {session_id}")
                    # Schedule async cleanup
                    asyncio.create_task(self.unregister_session(session_id))

            except ValueError:
                logger.warning(f"WebSocket not found in session: {session_id}")

    async def get_sessions_for_user_conversation(
        self,
        user_id: int,
        conversation_id: int
    ) -> list[str]:
        """
        Get all session_ids for a user's conversation from Redis.

        Args:
            user_id: The user's ID
            conversation_id: The conversation ID

        Returns:
            List of session_ids registered for this user/conversation
        """
        logger = get_ws_server_logger()

        try:
            redis = await redis_connection.get_client()
            key = CacheKeys.ws_user_conversation_sessions(user_id, conversation_id)
            members = await redis.smembers(key)
            return list(members) if members else []
        except Exception as e:
            logger.error(f"Failed to get sessions from Redis: {e}")
            return []

    async def broadcast_to_user_conversation(
        self,
        user_id: int,
        conversation_id: int,
        message: dict[str, Any]
    ) -> int:
        """
        Broadcast message to all sessions of a user's conversation.

        This enables sending notifications to all devices where a user
        has this conversation open.

        Args:
            user_id: The user's ID
            conversation_id: The conversation ID
            message: The message dict to send

        Returns:
            Total number of connections the message was sent to
        """
        logger = get_ws_server_logger()

        session_ids = await self.get_sessions_for_user_conversation(user_id, conversation_id)
        total_sent = 0

        for session_id in session_ids:
            sent = await self.send_to_session(session_id, message)
            total_sent += sent

        logger.info(
            f"Broadcast to user_id={user_id}, conversation_id={conversation_id}: "
            f"{total_sent} connections across {len(session_ids)} sessions"
        )
        return total_sent

    async def send_to_session(self, session_id: str, message: dict[str, Any]) -> int:
        """
        Send a message to all connections in a specific session.

        Args:
            session_id: The chat session ID to send to
            message: The message dict to send (will be JSON serialized)

        Returns:
            Number of connections the message was sent to
        """
        logger = get_ws_server_logger()

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

    def get_session_metadata(self, session_id: str) -> Optional[dict[str, Any]]:
        """
        Get metadata for a specific session.

        Args:
            session_id: The session ID

        Returns:
            Dict with user_id and conversation_id, or None if not found
        """
        return self.session_metadata.get(session_id)


manager = ConnectionManager()
