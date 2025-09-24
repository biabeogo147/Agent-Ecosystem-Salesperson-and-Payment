from a2a.types import AgentCard, AgentCapabilities
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from my_a2a_common import CREATE_ORDER_SKILL, QUERY_STATUS_SKILL
from my_a2a_common.a2a_salesperson_payment.constants import JSON_MEDIA_TYPE

from my_agent.payment_agent.agent import root_agent
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


a2a_app = to_a2a(
    root_agent,
    host=PAYMENT_AGENT_SERVER_HOST,
    port=PAYMENT_AGENT_SERVER_PORT,
    agent_card=_PAYMENT_AGENT_CARD,
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "my_agent.payment_agent.payment_a2a.a2a_app:a2a_app",
        host="0.0.0.0",
        port=PAYMENT_AGENT_SERVER_PORT,
    )