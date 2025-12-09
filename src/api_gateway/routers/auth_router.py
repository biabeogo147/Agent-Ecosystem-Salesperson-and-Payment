from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api_gateway.schemas import LoginRequest, LoginResponse, UserInfo
from src.api_gateway.services import authenticate_user, get_current_user
from src.utils.response_format import ResponseFormat
from src.utils.status import Status
from src.data.postgres.conversation_ops import (
    get_user_conversations,
    get_conversation_by_id,
    get_conversation_with_messages
)

auth_router = APIRouter(tags=["Authentication"])


@auth_router.post("/login")
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    result = await authenticate_user(request.username, request.password)

    if not result:
        return ResponseFormat(
            status=Status.FAILURE,
            message="Invalid username or password",
            data=None
        ).to_dict()

    return ResponseFormat(
        message="Login successful",
        data=LoginResponse(**result).model_dump()
    ).to_dict()


@auth_router.get("/conversations")
async def list_conversations(
    limit: int = Query(default=20, le=50, ge=1),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get list of user's recent conversations.
    Requires Bearer token in Authorization header.

    Returns:
        List of conversations with id, title, updated_at
    """
    conversations = await get_user_conversations(
        user_id=current_user.user_id,
        limit=limit
    )

    return ResponseFormat(
        data=[
            {
                "id": conv.id,
                "title": conv.title or f"Conversation #{conv.id}",
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None
            }
            for conv in conversations
        ]
    ).to_dict()


@auth_router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int,
    limit: int = Query(default=50, le=100, ge=1),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get messages for a specific conversation.
    Validates ownership: conversation must belong to current user.

    Returns:
        Conversation info and list of messages with role, content, created_at
    """
    # Verify ownership
    conv = await get_conversation_by_id(conversation_id)
    if not conv or conv.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    result = await get_conversation_with_messages(conversation_id, limit=limit)
    if not result:
        return ResponseFormat(
            data={
                "conversation": {
                    "id": conv.id,
                    "title": conv.title or f"Conversation #{conv.id}"
                },
                "messages": []
            }
        ).to_dict()

    conv, messages = result

    return ResponseFormat(
        data={
            "conversation": {
                "id": conv.id,
                "title": conv.title or f"Conversation #{conv.id}"
            },
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role.value.lower(),
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None
                }
                for msg in messages
            ]
        }
    ).to_dict()
