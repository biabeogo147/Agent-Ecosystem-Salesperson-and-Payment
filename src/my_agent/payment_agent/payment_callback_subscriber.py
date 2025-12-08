"""
Redis Pub/Sub subscriber for payment callbacks.

This module subscribes to the payment:callback Redis channel and processes
callback messages from the Payment Callback Service.

Simplified flow:
1. Receive order_id from Redis (published by Callback Service)
2. Call query_gateway_status which queries gateway AND updates order status
3. Notify Salesperson Agent via Redis Pub/Sub (only order_id + context_id)
4. Salesperson Agent will query order status via A2A (payment.query-status)
"""
import asyncio
import datetime
import json
from typing import Optional

from data.redis.cache_keys import CacheKeys
from src.data.redis.connection import redis_connection
from src.my_agent.payment_agent import a2a_payment_logger as logger
from src.my_agent.payment_agent.payment_mcp_client import query_gateway_status
from src.my_agent.my_a2a_common.payment_schemas.callback_message import CallbackMessage


async def process_callback(callback_data: dict) -> bool:
    """
    Process a payment callback message.

    Simplified flow:
    1. Receive order_id from Redis
    2. Call query_gateway_status (which queries gateway AND updates order)

    Args:
        callback_data: Callback message data from Redis (only order_id + timestamp)

    Returns:
        True if processed successfully, False otherwise
    """
    try:
        callback_message = CallbackMessage.model_validate(callback_data)

        logger.info(f"Processing callback for order_id={callback_message.order_id}")

        result = await query_gateway_status(order_id=callback_message.order_id)

        gateway_response = result.get("gateway_response", {})
        order = result.get("order", {})
        actual_status = gateway_response.get("status", "unknown")
        transaction_id = gateway_response.get("transaction_id")

        logger.info(
            f"Order {callback_message.order_id} processed: "
            f"gateway_status={actual_status}, transaction_id={transaction_id}, "
            f"order_status={order.get('status')}"
        )

        # Notify Salesperson Agent about the callback
        # Include user_id and conversation_id for multi-session broadcasting
        await notify_salesperson(
            order_id=callback_message.order_id,
            context_id=order.get("context_id", ""),
            user_id=order.get("user_id"),
            conversation_id=order.get("conversation_id")
        )

        return True

    except Exception as e:
        logger.error(f"Failed to process callback: {e}")
        return False


async def notify_salesperson(
    order_id: int,
    context_id: str,
    user_id: Optional[int] = None,
    conversation_id: Optional[int] = None
) -> bool:
    """
    Notify Salesperson Agent about payment callback via Redis Pub/Sub.

    Publishes a notification message to the salesperson:notification channel
    with user_id and conversation_id for multi-session broadcasting.

    Args:
        order_id: The order ID
        context_id: The context ID linking to Salesperson Agent session
        user_id: The user ID for multi-session lookup
        conversation_id: The conversation ID for multi-session lookup

    Returns:
        True if notification was published successfully, False otherwise
    """
    try:
        redis_client = await redis_connection.get_client()

        message = {
            "order_id": order_id,
            "context_id": context_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
        }

        await redis_client.publish(
            CacheKeys.salesperson_notification(),
            json.dumps(message)
        )
        logger.info(
            f"Published notification to Salesperson: "
            f"order_id={order_id}, context_id={context_id}, "
            f"user_id={user_id}, conversation_id={conversation_id}"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to notify Salesperson: {e}")
        return False


async def start_callback_subscriber() -> None:
    """
    Start the Redis subscriber for payment callbacks.

    This function subscribes to the payment:callback channel and processes
    messages indefinitely. It should be run as a background task.
    """
    logger.info(f"Starting payment callback subscriber on channel: {CacheKeys.payment_callback()}")

    try:
        redis_client = await redis_connection.get_client()
        pubsub = redis_client.pubsub()

        await pubsub.subscribe(CacheKeys.payment_callback())
        logger.info(f"Subscribed to Redis channel: {CacheKeys.payment_callback()}")

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")

                    callback_data = json.loads(data)
                    logger.debug(f"Received callback message: {callback_data}")

                    asyncio.create_task(process_callback(callback_data))

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse callback message: {e}")
                except Exception as e:
                    logger.error(f"Error processing callback message: {e}")

    except asyncio.CancelledError:
        logger.info("Callback subscriber cancelled")
        raise
    except Exception as e:
        logger.error(f"Callback subscriber error: {e}")
        raise
    finally:
        logger.info("Callback subscriber stopped")


_subscriber_task: Optional[asyncio.Task] = None


def start_subscriber_background() -> asyncio.Task:
    """
    Start the callback subscriber as a background task.

    Returns:
        The asyncio Task running the subscriber
    """
    global _subscriber_task
    _subscriber_task = asyncio.create_task(start_callback_subscriber())
    logger.info("Payment callback subscriber started as background task")
    return _subscriber_task


async def stop_subscriber() -> None:
    """Stop the callback subscriber background task."""
    global _subscriber_task
    if _subscriber_task and not _subscriber_task.done():
        _subscriber_task.cancel()
        try:
            await _subscriber_task
        except asyncio.CancelledError:
            pass
        logger.info("Payment callback subscriber stopped")
    _subscriber_task = None
