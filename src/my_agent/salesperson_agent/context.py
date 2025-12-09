"""Context variables for salesperson agent execution."""
from contextvars import ContextVar

# Context variable to store current user_id during agent execution
current_user_id: ContextVar[int] = ContextVar('current_user_id')
current_conversation_id: ContextVar[int] = ContextVar('current_conversation_id')


def get_current_user_id() -> int:
    """Get current user_id from context.

    Returns:
        The user_id set for the current execution context.

    Raises:
        LookupError: If user_id has not been set in the current context.
    """
    return current_user_id.get()


def get_current_conversation_id() -> int:
    """Get current conversation_id from context.

    Returns:
        The conversation_id set for the current execution context.

    Raises:
        LookupError: If conversation_id has not been set in the current context.
    """
    return current_conversation_id.get()
