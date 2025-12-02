"""
Redis Pub/Sub subscriber for salesperson notifications.

This module subscribes to the salesperson:notification Redis channel and processes
notification messages from the Payment Agent.

Simplified flow:
1. Receive notification from Redis (order_id, context_id, user_id, conversation_id)
2. Query order status via A2A (payment.query-status) to get actual status
3. Push notification to WebSocket clients via:
   - Multi-session broadcast if user_id and conversation_id provided
   - Fallback to context_id as session_id for backwards compatibility

Callback signature: async def callback(session_id: str, message: dict) -> None
"""
import asyncio
import json
from typing import Awaitable, Callable, Optional

from pydantic import BaseModel

from data.redis.cache_keys import CacheKeys
from src.data.redis.connection import redis_connection
from src.my_agent.salesperson_agent import salesperson_agent_logger as logger

# Type alias for notification callback
NotificationCallback = Callable[[str, dict], Awaitable[None]]

# Global callback reference
_notification_callback: NotificationCallback | None = None


class SalespersonNotification(BaseModel):
    """Schema for salesperson notification message from Payment Agent."""
    order_id: str
    context_id: str
    user_id: Optional[int] = None
    conversation_id: Optional[str] = None
    timestamp: str


async def process_notification(notification_data: dict) -> bool:
    """
    Process a salesperson notification message.

    Flow:
    1. Parse notification message (order_id, context_id, user_id, conversation_id)
    2. Query order status via A2A (payment.query-status)
    3. Push status to WebSocket clients:
       - Use broadcast_to_user_conversation if user_id and conversation_id present
       - Fallback to callback with context_id as session_id

    Args:
        notification_data: Notification message data from Redis

    Returns:
        True if processed successfully, False otherwise
    """
    from src.my_agent.salesperson_agent.salesperson_a2a.salesperson_a2a_client import query_payment_order_status
    from src.my_agent.salesperson_agent.websocket_server.connection_manager import manager

    global _notification_callback

    try:
        notification = SalespersonNotification.model_validate(notification_data)

        logger.info(
            f"Received payment notification: order_id={notification.order_id}, "
            f"context_id={notification.context_id}, "
            f"user_id={notification.user_id}, "
            f"conversation_id={notification.conversation_id}"
        )

        payment_response = await query_payment_order_status(
            context_id=notification.context_id,
            order_id=notification.order_id,
        )

        status = payment_response.get("status", {}).get("value", "unknown")
        logger.info(f"Order {notification.order_id} status queried via A2A: status={status}")

        if status == "SUCCESS":
            logger.info(f"Payment SUCCESS for order {notification.order_id}")
        elif status == "CANCELLED":
            logger.info(f"Payment CANCELLED for order {notification.order_id}")
        elif status == "FAILED":
            logger.warning(f"Payment FAILED for order {notification.order_id}")
        else:
            logger.info(f"Payment status '{status}' for order {notification.order_id}")

        # Build notification message
        message = {
            "type": "payment_status",
            "order_id": notification.order_id,
            "context_id": notification.context_id,
            "status": status,
            "timestamp": notification.timestamp
        }

        # Multi-session broadcast via Redis lookup if user_id and conversation_id present
        if notification.user_id and notification.conversation_id:
            sent_count = await manager.broadcast_to_user_conversation(
                user_id=notification.user_id,
                conversation_id=notification.conversation_id,
                message=message
            )
            logger.info(
                f"Notification broadcast: user_id={notification.user_id}, "
                f"conversation_id={notification.conversation_id}, "
                f"sent_to={sent_count} connections"
            )
        elif _notification_callback:
            # Fallback: Use context_id as session_id (backwards compatible)
            await _notification_callback(notification.context_id, message)
            logger.info(f"Notification pushed via callback for context: {notification.context_id}")
        else:
            logger.warning(
                "No user_id/conversation_id for multi-session broadcast "
                "and no callback registered, skipping push notification"
            )

        return True

    except Exception as e:
        logger.error(f"Failed to process notification: {e}")
        return False


async def start_notification_subscriber() -> None:
    """
    Start the Redis subscriber for salesperson notifications.

    This function subscribes to the salesperson:notification channel and processes
    messages indefinitely. It should be run as a background task.
    """
    logger.info(
        f"Starting salesperson notification subscriber on channel: "
        f"{CacheKeys.salesperson_notification()}"
    )

    try:
        redis_client = await redis_connection.get_client()
        pubsub = redis_client.pubsub()

        await pubsub.subscribe(CacheKeys.salesperson_notification())
        logger.info(f"Subscribed to Redis channel: {CacheKeys.salesperson_notification()}")

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")

                    notification_data = json.loads(data)
                    logger.debug(f"Received notification message: {notification_data}")

                    asyncio.create_task(process_notification(notification_data))

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse notification message: {e}")
                except Exception as e:
                    logger.error(f"Error processing notification message: {e}")

    except asyncio.CancelledError:
        logger.info("Notification subscriber cancelled")
        raise
    except Exception as e:
        logger.error(f"Notification subscriber error: {e}")
        raise
    finally:
        logger.info("Notification subscriber stopped")


_subscriber_task: Optional[asyncio.Task] = None


def start_subscriber_background() -> asyncio.Task:
    """
    Start the notification subscriber as a background task (without callback).

    Returns:
        The asyncio Task running the subscriber
    """
    global _subscriber_task
    _subscriber_task = asyncio.create_task(start_notification_subscriber())
    logger.info("Salesperson notification subscriber started as background task")
    return _subscriber_task


def start_subscriber_with_callback(callback: NotificationCallback) -> asyncio.Task:
    """
    Start the notification subscriber with a callback for pushing notifications.

    This is the preferred method when integrating with WebSocket server.
    The callback will be called for each processed notification with:
    - session_id: str - The chat session ID (from Order.context_id)
    - message: dict - The notification message to push

    Note: If user_id and conversation_id are present in the notification,
    the multi-session broadcast via Redis will be used instead of the callback.

    Args:
        callback: Async function to call when notification is processed

    Returns:
        The asyncio Task running the subscriber
    """
    global _subscriber_task, _notification_callback

    _notification_callback = callback
    _subscriber_task = asyncio.create_task(start_notification_subscriber())
    logger.info("Salesperson notification subscriber started with callback")
    return _subscriber_task


async def stop_subscriber() -> None:
    """Stop the notification subscriber background task."""
    global _subscriber_task, _notification_callback

    if _subscriber_task and not _subscriber_task.done():
        _subscriber_task.cancel()
        try:
            await _subscriber_task
        except asyncio.CancelledError:
            pass
        logger.info("Salesperson notification subscriber stopped")

    _subscriber_task = None
    _notification_callback = None
