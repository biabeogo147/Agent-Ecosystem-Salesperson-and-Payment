"""Functions that publish the a2a_payment agent's ``AgentCard``."""

from a2a.types import AgentCapabilities, AgentCard

from .constants import JSON_MEDIA_TYPE
from .skills import CREATE_ORDER_SKILL, QUERY_STATUS_SKILL


def build_payment_agent_card(base_url: str) -> AgentCard:
    """Describe the a2a_payment agent using the official SDK models.

    Parameters
    ----------
    base_url:
        The JSON-RPC endpoint where other agents can reach the a2a_payment agent.

    The resulting card highlights how each field of :class:`AgentCard` is used:

    ``name`` and ``description``
        Human friendly metadata for discovery.
    ``version``
        The a2a_payment agent's own release number so clients can reason about
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
        Lists the :class:`AgentSkill` objects declared in :mod:`my_a2a.a2a_payment.skills`.
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

__all__ = ["build_payment_agent_card"]
