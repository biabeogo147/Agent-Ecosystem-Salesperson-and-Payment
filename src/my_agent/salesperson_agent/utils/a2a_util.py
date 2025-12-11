from __future__ import annotations

from a2a.types import AgentCard, AgentCapabilities

from my_agent.my_a2a_common.constants import JSON_MEDIA_TYPE
from my_agent.salesperson_agent.agent import _DESCRIPTION
from my_agent.salesperson_agent.salesperson_a2a.salesperson_agent_skills import SALESPERSON_SKILLS


def build_salesperson_agent_card(base_url: str) -> AgentCard:
    """
    Build the A2A agent card for the salesperson agent.

    Args:
        base_url: The base URL for the agent service

    Returns:
        AgentCard describing the salesperson agent capabilities
    """
    capabilities = AgentCapabilities(
        streaming=True,
        push_notifications=False,
        state_transition_history=False,
    )

    return AgentCard(
        name="Salesperson Agent",
        description=_DESCRIPTION,
        version="1.0.0",
        url=base_url,
        default_input_modes=[JSON_MEDIA_TYPE],
        default_output_modes=[JSON_MEDIA_TYPE],
        capabilities=capabilities,
        skills=SALESPERSON_SKILLS,
    )
