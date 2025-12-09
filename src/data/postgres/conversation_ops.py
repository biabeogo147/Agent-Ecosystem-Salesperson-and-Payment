"""Database operations for Conversation entity."""

from sqlalchemy import select

from src.data.postgres.connection import db_connection
from src.data.models.db_entity.conversation import Conversation
from src.data.models.db_entity.message import Message
from src.utils.logger import get_current_logger


async def create_conversation(user_id: int, title: str = None) -> Conversation:
    """
    Create a new conversation.

    Args:
        user_id: User ID who owns the conversation
        title: Optional title for the conversation

    Returns:
        Created Conversation object with integer ID
    """
    logger = get_current_logger()
    session = db_connection.get_session()
    async with session:
        conv = Conversation(user_id=user_id, title=title)
        session.add(conv)
        await session.commit()
        await session.refresh(conv)
        logger.info(f"Created new conversation: id={conv.id}, user_id={user_id}")
        return conv


async def get_conversation_by_id(conversation_id: int) -> Conversation | None:
    """
    Get conversation by integer ID.

    Args:
        conversation_id: Integer ID of conversation

    Returns:
        Conversation object or None if not found
    """
    session = db_connection.get_session()
    async with session:
        result = await session.execute(
            select(Conversation).filter(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()


async def get_conversation_with_messages(
    conversation_id: int,
    limit: int = 20
) -> tuple[Conversation, list[Message]] | None:
    """
    Get conversation and recent messages.

    Args:
        conversation_id: Integer ID of conversation
        limit: Maximum number of recent messages to return

    Returns:
        Tuple of (Conversation, list[Message]) or None if not found
    """
    session = db_connection.get_session()
    async with session:
        result = await session.execute(
            select(Conversation).filter(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()

        if not conv:
            return None

        result = await session.execute(
            select(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.id.desc())
            .limit(limit)
        )
        messages = list(reversed(result.scalars().all()))  # Oldest first

        return conv, messages


async def update_conversation_title(conversation_id: int, title: str) -> bool:
    """
    Update conversation title.

    Args:
        conversation_id: Integer ID of conversation
        title: New title

    Returns:
        True if updated, False if not found
    """
    logger = get_current_logger()
    session = db_connection.get_session()
    async with session:
        result = await session.execute(
            select(Conversation).filter(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv:
            conv.title = title
            await session.commit()
            logger.debug(f"Updated title for conversation {conversation_id}: {title}")
            return True
        return False


async def update_conversation_summary(conversation_id: int, summary: str) -> bool:
    """
    Update conversation summary.

    Args:
        conversation_id: Integer ID of conversation
        summary: New summary text

    Returns:
        True if updated, False if not found
    """
    logger = get_current_logger()
    session = db_connection.get_session()
    async with session:
        result = await session.execute(
            select(Conversation).filter(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv:
            conv.summary = summary
            await session.commit()
            logger.debug(f"Updated summary for conversation {conversation_id}")
            return True
        return False


async def get_user_conversations(user_id: int, limit: int = 20) -> list[Conversation]:
    """
    Get recent conversations for a user.

    Args:
        user_id: User ID
        limit: Maximum number of conversations to return

    Returns:
        List of Conversation objects, ordered by most recent first
    """
    session = db_connection.get_session()
    async with session:
        result = await session.execute(
            select(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc().nullsfirst())
            .limit(limit)
        )
        return list(result.scalars().all())
