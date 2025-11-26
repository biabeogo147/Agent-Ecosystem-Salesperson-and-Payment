"""
Redis Pub/Sub subscriber for payment callbacks.

This module subscribes to the payment:callback Redis channel and processes
callback messages from the Payment Callback Service.

Simplified flow:
1. Receive order_id from Redis (published by Callback Service)
2. Call query_gateway_status which queries gateway AND updates order status
"""
import asyncio
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

        result = await query_gateway_status(payload={
            "order_id": callback_message.order_id
        })

        gateway_response = result.get("gateway_response", {})
        order = result.get("order", {})
        actual_status = gateway_response.get("status", "unknown")
        transaction_id = gateway_response.get("transaction_id")

        logger.info(
            f"Order {callback_message.order_id} processed: "
            f"gateway_status={actual_status}, transaction_id={transaction_id}, "
            f"order_status={order.get('status')}"
        )

        # Placeholder: Notify Salesperson Agent (future implementation)
        # await notify_salesperson(callback.order_id, actual_status)

        return True

    except Exception as e:
        logger.error(f"Failed to process callback: {e}")
        return False


async def notify_salesperson(order_id: str, status: str) -> None:
    """
    Placeholder: Notify Salesperson Agent about payment status change.

    This will be implemented when Salesperson Agent notification is needed.
    Will use Redis Pub/Sub to publish to salesperson:notification channel.
    """
    # TODO: Implement when needed
    logger.debug(f"Placeholder: Would notify Salesperson about order {order_id} status={status}")
    pass


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
