import asyncio
import json

from src.data.redis.connection import redis_connection
from src.data.redis.cache_keys import CacheKeys
from src.websocket_server.connection_manager import manager


async def start_notification_receiver() -> None:
    """
    Subscribe to Redis channel for payment notifications from Salesperson Agent.

    Receives notifications published by Salesperson Agent and broadcasts them
    to connected WebSocket clients based on user_id and conversation_id.
    """
    from src.websocket_server import get_ws_server_logger

    logger = get_ws_server_logger()
    logger.info("Starting notification receiver...")

    try:
        redis = await redis_connection.get_client()
        pubsub = redis.pubsub()

        await pubsub.subscribe(CacheKeys.websocket_notification())
        logger.info(f"Subscribed to Redis channel: {CacheKeys.websocket_notification()}")

        async for message in pubsub.listen():
            if message["type"] == "payment_status":
                try:
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")

                    notification = json.loads(data)
                    logger.debug(f"Received notification: {notification}")

                    # Broadcast to users based on user_id and conversation_id
                    user_id = notification.get("user_id")
                    conversation_id = notification.get("conversation_id")

                    if user_id and conversation_id:
                        sent_count = await manager.broadcast_to_user_conversation(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            message=notification
                        )
                        logger.info(
                            f"Broadcast notification to {sent_count} connections: "
                            f"user_id={user_id}, conversation_id={conversation_id}"
                        )
                    else:
                        logger.warning(f"Notification missing user_id or conversation_id: {notification}")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse notification message: {e}")
                except Exception as e:
                    logger.error(f"Error processing notification: {e}")

    except asyncio.CancelledError:
        logger.info("Notification receiver cancelled")
        raise
    except Exception as e:
        logger.error(f"Notification receiver error: {e}")
        raise
