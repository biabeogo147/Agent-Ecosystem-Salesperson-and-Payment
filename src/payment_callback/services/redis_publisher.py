import json
from datetime import datetime

from src.config import REDIS_CHANNEL_PAYMENT_CALLBACK
from src.data.redis.connection import redis_connection
from src.payment_callback import callback_logger


async def publish_payment_callback(order_id: str) -> bool:
    """
    Publish payment callback to Redis channel.
    Only publishes order_id - Payment Agent will query gateway for actual status.

    Args:
        order_id: Order ID from payment gateway callback

    Returns:
        True if published successfully, False otherwise
    """
    try:
        redis_client = await redis_connection.get_client()

        message = {
            "order_id": order_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        await redis_client.publish(REDIS_CHANNEL_PAYMENT_CALLBACK, json.dumps(message))

        callback_logger.info(f"Published callback to Redis: order_id={order_id}")
        return True

    except Exception as e:
        callback_logger.error(f"Failed to publish callback to Redis: {e}")
        return False
