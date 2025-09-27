from collections.abc import AsyncGenerator

from a2a.server.apps.jsonrpc.starlette_app import A2AStarletteApplication
from a2a.server.context import ServerCallContext
from a2a.server.events.event_queue import Event
from a2a.server.request_handlers.request_handler import RequestHandler
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    DeleteTaskPushNotificationConfigParams,
    GetTaskPushNotificationConfigParams,
    InternalError,
    InvalidParamsError,
    ListTaskPushNotificationConfigParams,
    Message,
    MessageSendParams,
    Task,
    TaskIdParams,
    TaskPushNotificationConfig,
    TaskQueryParams,
    UnsupportedOperationError,
)
from a2a.utils.errors import ServerError
from pydantic import ValidationError
from starlette.applications import Starlette

from my_a2a_common import CREATE_ORDER_SKILL, QUERY_STATUS_SKILL
from my_a2a_common.a2a_salesperson_payment.constants import JSON_MEDIA_TYPE

from my_agent.payment_agent.payment_a2a.payment_agent_handler import (
    PaymentAgentHandler,
)
from my_agent.payment_agent.payment_mcp_client import (
    create_order,
    query_order_status,
)
from config import PAYMENT_AGENT_SERVER_HOST, PAYMENT_AGENT_SERVER_PORT


def build_payment_agent_card(base_url: str) -> AgentCard:
    """Describe the payment agent using the official SDK models.

    Parameters
    ----------
    base_url:
        The JSON-RPC endpoint where other agents can reach the payment agent.

    The resulting card highlights how each field of :class:`AgentCard` is used:
    ``name`` and ``description``
        Human friendly metadata for discovery.
    ``version``
        The payment agent's own release number so clients can reason about
        backwards compatibility.
    ``url``
        Entry point where :class:`~a2a.types.MessageSendParams` requests should
        be POSTed.
    ``default_input_modes`` / ``default_output_modes``
        Express that the agent expects JSON payloads by default.
    ``capabilities``
        Flags whether the agent supports streaming, push notifications or
        publishes state transition history. We disable the advanced features to
        keep the tutorial simple.
    ``skills``
        Lists the :class:`AgentSkill` objects declared in :mod:`my_a2a_common.payment.skills`.
    """

    capabilities = AgentCapabilities(
        streaming=False,
        push_notifications=False,
        state_transition_history=False,
    )

    return AgentCard(
        name="Payment Agent",
        description="Processes checkout requests coming from the salesperson agent.",
        version="1.0.0",
        url=base_url,
        default_input_modes=[JSON_MEDIA_TYPE],
        default_output_modes=[JSON_MEDIA_TYPE],
        capabilities=capabilities,
        skills=[CREATE_ORDER_SKILL, QUERY_STATUS_SKILL],
    )


_CARD_BASE_URL = f"http://{PAYMENT_AGENT_SERVER_HOST}:{PAYMENT_AGENT_SERVER_PORT}/"
_PAYMENT_AGENT_CARD = build_payment_agent_card(_CARD_BASE_URL)


class _PaymentJsonRpcRequestHandler(RequestHandler):
    """Minimal JSON-RPC handler that delegates to :class:`PaymentAgentHandler`."""

    def __init__(self, handler: PaymentAgentHandler) -> None:
        self._handler = handler

    async def on_message_send(
        self,
        params: MessageSendParams,
        context: ServerCallContext | None = None,
    ) -> Message:
        metadata = params.metadata or {}
        task_payload = metadata.get("task")
        if task_payload is None:
            raise ServerError(
                error=InvalidParamsError(message="Request metadata is missing the task payload."),
            )

        try:
            task = Task.model_validate(task_payload)
        except ValidationError as exc:
            raise ServerError(
                error=InvalidParamsError(message="Task payload is not a valid A2A task."),
            ) from exc

        try:
            return await self._handler.handle_task(task)
        except ValueError as exc:
            raise ServerError(error=InvalidParamsError(message=str(exc))) from exc
        except Exception as exc:  # pragma: no cover - defensive guard
            raise ServerError(
                error=InternalError(message="Payment handler failed to process the task."),
            ) from exc

    async def on_message_send_stream(
        self,
        params: MessageSendParams,
        context: ServerCallContext | None = None,
    ) -> AsyncGenerator[Event, None]:
        raise ServerError(error=UnsupportedOperationError())
        yield  # pragma: no cover

    async def on_get_task(
        self,
        params: TaskQueryParams,
        context: ServerCallContext | None = None,
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())

    async def on_cancel_task(
        self,
        params: TaskIdParams,
        context: ServerCallContext | None = None,
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())

    async def on_set_task_push_notification_config(
        self,
        params: TaskPushNotificationConfig,
        context: ServerCallContext | None = None,
    ) -> TaskPushNotificationConfig:
        raise ServerError(error=UnsupportedOperationError())

    async def on_get_task_push_notification_config(
        self,
        params: TaskIdParams | GetTaskPushNotificationConfigParams,
        context: ServerCallContext | None = None,
    ) -> TaskPushNotificationConfig:
        raise ServerError(error=UnsupportedOperationError())

    async def on_list_task_push_notification_config(
        self,
        params: ListTaskPushNotificationConfigParams,
        context: ServerCallContext | None = None,
    ) -> list[TaskPushNotificationConfig]:
        raise ServerError(error=UnsupportedOperationError())

    async def on_delete_task_push_notification_config(
        self,
        params: DeleteTaskPushNotificationConfigParams,
        context: ServerCallContext | None = None,
    ) -> None:
        raise ServerError(error=UnsupportedOperationError())

    async def on_resubscribe_to_task(
        self,
        params: TaskIdParams,
        context: ServerCallContext | None = None,
    ) -> AsyncGenerator[Event, None]:
        raise ServerError(error=UnsupportedOperationError())
        yield  # pragma: no cover


payment_handler = PaymentAgentHandler(
    create_order_tool=create_order,
    query_status_tool=query_order_status,
)

_request_handler = _PaymentJsonRpcRequestHandler(payment_handler)
_a2a_application = A2AStarletteApplication(
    agent_card=_PAYMENT_AGENT_CARD,
    http_handler=_request_handler,
)

_starlette_app = Starlette()
_a2a_application.add_routes_to_app(_starlette_app)

a2a_app = _starlette_app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "my_agent.payment_agent.payment_a2a.a2a_app:a2a_app",
        host="0.0.0.0",
        port=PAYMENT_AGENT_SERVER_PORT,
    )