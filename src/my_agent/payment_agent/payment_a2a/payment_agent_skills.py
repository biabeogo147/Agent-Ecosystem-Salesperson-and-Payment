from a2a.types import AgentSkill

from src.my_agent.my_a2a_common.constants import JSON_MEDIA_TYPE

# Each skill gets a stable identifier. This is what tasks will reference in their
# metadata when they ask the payment agent to execute a capability.
CREATE_ORDER_SKILL_ID = "payment.create-order"
QUERY_STATUS_SKILL_ID = "payment.query-status"

# The payment agent only accepts and returns JSON payloads, so we describe that in
# both the input and output modes.
COMMON_MODES = [JSON_MEDIA_TYPE]

# Skill definitions reuse the SDK models so newcomers see the official fields
# (id, name, description, tags, examples, etc.) exactly as the protocol defines
# them. The comments explain why each field matters in this particular flow.
CREATE_ORDER_SKILL = AgentSkill(
    id=CREATE_ORDER_SKILL_ID,
    name="Create payment order",
    description="Accepts checkout details and opens a payment order with the gateway.",
    tags=["payment", "order"],
    input_modes=COMMON_MODES,
    output_modes=COMMON_MODES,
    examples=["Create a payment for the cart currently in checkout."],
)

QUERY_STATUS_SKILL = AgentSkill(
    id=QUERY_STATUS_SKILL_ID,
    name="Query payment status",
    description="Looks up the latest status of a previously created payment order.",
    tags=["payment", "status"],
    input_modes=COMMON_MODES,
    output_modes=COMMON_MODES,
    examples=["Check if the payment with correlation ID ABC completed."],
)
