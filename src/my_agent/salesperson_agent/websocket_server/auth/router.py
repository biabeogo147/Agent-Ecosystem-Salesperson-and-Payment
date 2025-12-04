from fastapi import APIRouter

from src.my_agent.salesperson_agent.websocket_server.auth.schemas import LoginRequest, LoginResponse
from src.my_agent.salesperson_agent.websocket_server.auth.services import authenticate_user
from src.utils.response_format import ResponseFormat
from src.utils.status import Status

router = APIRouter(tags=["Authentication"])


@router.post("/login")
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
