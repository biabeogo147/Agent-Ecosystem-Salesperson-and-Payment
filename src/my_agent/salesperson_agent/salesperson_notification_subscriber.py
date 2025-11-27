"""
Redis Pub/Sub subscriber for salesperson notifications.

This module subscribes to the salesperson:notification Redis channel and processes
notification messages from the Payment Agent.

Simplified flow:
1. Receive notification from Redis (order_id + context_id only)
2. Query order status via A2A (payment.query-status) to get actual status
3. Process notification (log or notify user via frontend integration)
"""
import asyncio
import json
from typing import Optional

from pydantic import BaseModel

from data.redis.cache_keys import CacheKeys
from src.data.redis.connection import redis_connection
from src.my_agent.salesperson_agent import salesperson_agent_logger as logger


class SalespersonNotification(BaseModel):
    """Schema for salesperson notification message from Payment Agent."""
    order_id: str
    context_id: str
    timestamp: str


async def process_notification(notification_data: dict) -> bool:
    """
    Process a salesperson notification message.

    Flow:
    1. Parse notification message (order_id + context_id)
    2. Query order status via A2A (payment.query-status)
    3. Log the result (actual user notification depends on frontend integration)

    Args:
        notification_data: Notification message data from Redis

    Returns:
        True if processed successfully, False otherwise
    """
    try:
        notification = SalespersonNotification.model_validate(notification_data)

        logger.info(
            f"Received payment notification: "
            f"order_id={notification.order_id}, "
            f"context_id={notification.context_id}"
        )

        # Query order status via A2A to get actual status
        from src.my_agent.salesperson_agent.salesperson_a2a.salesperson_a2a_client import (
            get_salesperson_a2a_client
        )
        a2a_client = get_salesperson_a2a_client()
        payment_response = await a2a_client.query_status(
            context_id=notification.context_id,
            order_id=notification.order_id
        )

        # Log result based on queried status
        status = payment_response.status.value if payment_response.status else "unknown"
        logger.info(
            f"Order {notification.order_id} status queried via A2A: status={status}"
        )

        if status == "SUCCESS":
            logger.info(f"Payment SUCCESS for order {notification.order_id}")
        elif status == "CANCELLED":
            logger.info(f"Payment CANCELLED for order {notification.order_id}")
        elif status == "FAILED":
            logger.warning(f"Payment FAILED for order {notification.order_id}")
        else:
            logger.info(f"Payment status '{status}' for order {notification.order_id}")

        # TODO: Integrate with frontend/WebSocket to notify user in real-time
        # This depends on how the frontend is implemented (WebSocket, SSE, polling, etc.)

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
    Start the notification subscriber as a background task.

    Returns:
        The asyncio Task running the subscriber
    """
    global _subscriber_task
    _subscriber_task = asyncio.create_task(start_notification_subscriber())
    logger.info("Salesperson notification subscriber started as background task")
    return _subscriber_task


async def stop_subscriber() -> None:
    """Stop the notification subscriber background task."""
    global _subscriber_task
    if _subscriber_task and not _subscriber_task.done():
        _subscriber_task.cancel()
        try:
            await _subscriber_task
        except asyncio.CancelledError:
            pass
        logger.info("Salesperson notification subscriber stopped")
    _subscriber_task = None
