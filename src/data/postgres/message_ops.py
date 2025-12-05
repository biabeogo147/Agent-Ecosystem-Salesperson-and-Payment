"""Database operations for Message entity."""

from sqlalchemy import select

from src.data.postgres.connection import db_connection
from src.data.models.db_entity.message import Message
from src.data.models.enum.message_role import MessageRole
from src.utils.logger import get_current_logger


async def save_message(conversation_id: int, role: MessageRole, content: str) -> Message:
    """
    Save a single message to DB.

    Args:
        conversation_id: Integer ID of conversation
        role: MessageRole enum (USER, ASSISTANT, SYSTEM)
        content: Message content text

    Returns:
        Created Message object
    """
    logger = get_current_logger()
    session = db_connection.get_session()
    async with session:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content
        )
        session.add(message)
        await session.commit()
        await session.refresh(message)
        logger.debug(f"Saved message for conversation {conversation_id}: role={role.value}")
        return message


async def save_user_assistant_pair(
    conversation_id: int,
    user_message: str,
    assistant_message: str
) -> tuple[Message, Message]:
    """
    Save user message and assistant response as a pair.

    Args:
        conversation_id: Integer ID of conversation
        user_message: User's message content
        assistant_message: Assistant's response content

    Returns:
        Tuple of (user_message, assistant_message) Message objects
    """
    logger = get_current_logger()
    session = db_connection.get_session()
    async with session:
        user_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=user_message
        )
        assistant_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=assistant_message
        )
        session.add_all([user_msg, assistant_msg])
        await session.commit()

        logger.debug(f"Saved message pair for conversation {conversation_id}")
        return user_msg, assistant_msg


async def get_recent_messages(conversation_id: int, limit: int = 20) -> list[Message]:
    """
    Get recent messages for a conversation.

    Args:
        conversation_id: Integer ID of conversation
        limit: Maximum number of messages to return

    Returns:
        List of Message objects, ordered oldest first
    """
    session = db_connection.get_session()
    async with session:
        result = await session.execute(
            select(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = list(reversed(result.scalars().all()))  # Oldest first
        return messages


async def get_messages_since(conversation_id: int, since_id: int) -> list[Message]:
    """
    Get messages after a specific message ID (for incremental loading).

    Args:
        conversation_id: Integer ID of conversation
        since_id: Message ID to start from (exclusive)

    Returns:
        List of Message objects created after since_id
    """
    session = db_connection.get_session()
    async with session:
        result = await session.execute(
            select(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.id > since_id
            )
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())


async def get_message_count(conversation_id: int) -> int:
    """
    Get total message count for a conversation.

    Args:
        conversation_id: Integer ID of conversation

    Returns:
        Number of messages in the conversation
    """
    from sqlalchemy import func

    session = db_connection.get_session()
    async with session:
        result = await session.execute(
            select(func.count(Message.id))
            .filter(Message.conversation_id == conversation_id)
        )
        return result.scalar() or 0
