"""Database operations for Order model."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.data.postgres.connection import db_connection
from src.data.models.db_entity.order import Order
from src.utils.logger import get_current_logger


async def get_order_by_id(order_id: int) -> Order | None:
    """
    Get an order by its ID with items eagerly loaded.

    Args:
        order_id: Order ID to search for

    Returns:
        Order object with items loaded if found, None otherwise
    """
    logger = get_current_logger()
    session = db_connection.get_session()
    try:
        async with session:
            result = await session.execute(
                select(Order)
                .options(selectinload(Order.items))
                .filter(Order.id == order_id)
            )
            return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error getting order by ID {order_id}: {e}")
        raise
