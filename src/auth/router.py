"""
Authentication router with login endpoint.
"""
from passlib.context import CryptContext
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, or_

from src.auth.schemas import LoginRequest, LoginResponse
from src.config import JWT_EXPIRE_MINUTES
from src.data.models.db_entity.user import User
from src.data.postgres.connection import db_connection
from src.utils.jwt_utils import create_access_token
from src.utils.logger import get_current_logger

router = APIRouter(tags=["Authentication"])

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger = get_current_logger()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a plain password."""
    return pwd_context.hash(password)


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """
    Authenticate user and return JWT token.

    Args:
        request: Login request with username/email and password

    Returns:
        LoginResponse with access_token and user info

    Raises:
        HTTPException: If credentials are invalid
    """
    session = db_connection.get_session()

    try:
        # Query user by username or email
        result = await session.execute(
            select(User).where(
                or_(
                    User.username == request.username,
                    User.email == request.username
                )
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"Login failed: user not found - {request.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        # Verify password
        if not verify_password(request.password, user.hashed_password):
            logger.warning(f"Login failed: invalid password - {request.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        # Create JWT token
        access_token = create_access_token(
            user_id=user.id,
            username=user.username
        )

        logger.info(f"Login successful: user_id={user.id}, username={user.username}")

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            username=user.username,
            expires_in=JWT_EXPIRE_MINUTES * 60  # Convert to seconds
        )

    finally:
        await session.close()


@router.get("/me")
async def get_current_user_info(
    user_info=None  # Will be injected via dependency
):
    """
    Get current authenticated user info.

    This endpoint requires authentication via get_current_user dependency.
    """
    from src.auth.dependencies import get_current_user
    # Note: This is a placeholder. In actual usage, add Depends(get_current_user)
    return {"message": "Use this endpoint with authentication dependency"}
