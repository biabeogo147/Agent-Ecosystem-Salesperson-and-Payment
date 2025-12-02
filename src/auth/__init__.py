"""
Authentication module for JWT-based authentication.
"""
from src.auth.router import router as auth_router
from src.auth.dependencies import get_current_user, get_current_user_optional

__all__ = ["auth_router", "get_current_user", "get_current_user_optional"]
