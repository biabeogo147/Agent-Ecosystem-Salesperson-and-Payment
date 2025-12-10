import asyncio
import json
from typing import Optional

from pydantic import BaseModel

from data.redis.cache_keys import CacheKeys
from src.data.redis.connection import redis_connection
from src.my_agent.salesperson_agent import salesperson_agent_logger as logger


class SalespersonNotification(BaseModel):
    """Schema for salesperson notification message from Payment Agent."""
    order_id: int
    context_id: str
    user_id: int
    conversation_id: int
    timestamp: str


def format_notification_message(status: str, order_id: int) -> str:
    """
    Format payment notification as human-readable message.

    Args:
        status: Payment status (SUCCESS, CANCELLED, FAILED, PENDING)
        order_id: Order ID

    Returns:
        Formatted message string
    """
    status_messages = {
        "SUCCESS": f"Đơn hàng #{order_id} đã thanh toán thành công!",
        "CANCELLED": f"Đơn hàng #{order_id} đã bị hủy.",
        "FAILED": f"Thanh toán đơn hàng #{order_id} thất bại.",
        "PENDING": f"Đơn hàng #{order_id} đang chờ thanh toán.",
    }
    return status_messages.get(status, f"Đơn hàng #{order_id}: {status}")


async def process_notification(notification_data: dict) -> bool:
    """
    Process a salesperson notification message.

    Flow:
    1. Parse notification message (order_id, context_id, user_id, conversation_id)
    2. Query order status via A2A (payment.query-status)
    3. Save notification as ASSISTANT message to DB
    4. Update Redis conversation cache
    5. Inject into ADK session (if active)
    6. Publish notification to Redis for WebSocket Server to consume

    Args:
        notification_data: Notification message data from Redis

    Returns:
        True if processed successfully, False otherwise
    """
    from src.my_agent.salesperson_agent.salesperson_a2a.salesperson_a2a_client import query_payment_order_status

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

        status = payment_response["result"]["response"]["status"]
        logger.info(f"Order {notification.order_id} status queried via A2A: status={status}")

        if status == "SUCCESS":
            logger.info(f"Payment SUCCESS for order {notification.order_id}")
        elif status == "CANCELLED":
            logger.info(f"Payment CANCELLED for order {notification.order_id}")
        elif status == "FAILED":
            logger.warning(f"Payment FAILED for order {notification.order_id}")
        else:
            logger.info(f"Payment status '{status}' for order {notification.order_id}")

        notification_message = format_notification_message(status, notification.order_id)

        # 1. Save to DB as ASSISTANT message
        if notification.conversation_id:
            try:
                from src.data.postgres.message_ops import save_message
                from src.data.models.enum.message_role import MessageRole

                await save_message(
                    conversation_id=notification.conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=notification_message
                )
                logger.info(f"Saved notification to DB: conv={notification.conversation_id}")
            except Exception as e:
                logger.error(f"Failed to save notification to DB: {e}")

            # 2. Update Redis conversation cache
            try:
                from src.data.redis.conversation_cache import append_single_message_to_cache

                await append_single_message_to_cache(
                    conversation_id=notification.conversation_id,
                    role="assistant",
                    content=notification_message
                )
                logger.info(f"Updated Redis cache: conv={notification.conversation_id}")
            except Exception as e:
                logger.error(f"Failed to update Redis cache: {e}")

        # 3. Inject into ADK session (if active)
        if notification.user_id and notification.conversation_id:
            try:
                from src.my_agent.salesperson_agent.routers.agent_router import get_session_service
                from src.my_agent.salesperson_agent.services import inject_single_message_to_session

                session_service = get_session_service()
                if session_service:
                    injected = await inject_single_message_to_session(
                        session_service=session_service,
                        user_id=notification.user_id,
                        conversation_id=notification.conversation_id,
                        message=notification_message
                    )
                    if injected:
                        logger.info(f"Injected notification to ADK session: conv={notification.conversation_id}")
                    else:
                        logger.debug(f"No active ADK session for injection: conv={notification.conversation_id}")
            except Exception as e:
                logger.error(f"Failed to inject to ADK session: {e}")

        # 4. Publish to WebSocket for browser notification
        message = {
            "type": "payment_status",
            "order_id": notification.order_id,
            "context_id": notification.context_id,
            "status": status,
            "timestamp": notification.timestamp,
            "user_id": notification.user_id,
            "conversation_id": notification.conversation_id
        }

        from src.data.redis.connection import redis_connection

        try:
            redis = await redis_connection.get_client()
            await redis.publish(
                CacheKeys.websocket_notification(),
                json.dumps(message)
            )
            logger.info(
                f"Published notification to WebSocket Server: order_id={notification.order_id}, "
                f"user_id={notification.user_id}, conversation_id={notification.conversation_id}"
            )
        except Exception as e:
            logger.error(f"Failed to publish notification to Redis: {e}")

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
