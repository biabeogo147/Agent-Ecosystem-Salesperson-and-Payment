"""
Async context utilities for preserving contextvars in background tasks.

This module patches asyncio.create_task to automatically copy context,
ensuring that context-aware logging works correctly in background tasks.

Problem:
    asyncio.create_task() creates a new task with its own context, which means
    contextvars (like app logger) are not automatically inherited from the parent task.

Solution:
    Monkey-patch asyncio.create_task to automatically copy the current context
    when creating new tasks.

Usage:
    # Call once at app startup, BEFORE any other imports that use create_task
    from src.utils.async_context import patch_asyncio_create_task
    patch_asyncio_create_task()
"""
import asyncio
from contextvars import copy_context
from typing import Coroutine, Optional

_original_create_task = asyncio.create_task
_is_patched = False


def _create_task_with_context(
    coro: Coroutine,
    *,
    name: Optional[str] = None,
    context=None
) -> asyncio.Task:
    """
    Create an asyncio task that inherits the current context.

    If no context is provided, automatically copies the current context
    so that contextvars (like app logger) are preserved in background tasks.

    Args:
        coro: The coroutine to run in the task
        name: Optional name for the task
        context: Optional context to run the task in. If None, copies current context.

    Returns:
        asyncio.Task: The created task with context preserved
    """
    if context is None:
        context = copy_context()
    return _original_create_task(coro, name=name, context=context)


def patch_asyncio_create_task():
    """
    Patch asyncio.create_task to automatically preserve context.

    Call this once at app startup, before any create_task calls.
    Safe to call multiple times (only patches once).

    Example:
        # At the top of your app entry point
        from src.utils.async_context import patch_asyncio_create_task
        patch_asyncio_create_task()

        # Now all asyncio.create_task() calls will preserve context
        asyncio.create_task(some_background_work())  # Context is preserved!
    """
    global _is_patched
    if not _is_patched:
        asyncio.create_task = _create_task_with_context
        _is_patched = True


def unpatch_asyncio_create_task():
    """
    Restore original asyncio.create_task behavior.

    Mainly useful for testing to ensure test isolation.
    """
    global _is_patched
    if _is_patched:
        asyncio.create_task = _original_create_task
        _is_patched = False


def is_patched() -> bool:
    """Check if asyncio.create_task has been patched."""
    return _is_patched
