"""
Salesperson Agent A2A Skills definitions.

These skills describe the capabilities of the salesperson agent
as per the A2A (Agent-to-Agent) protocol.
"""
from a2a.types import AgentSkill

from my_agent.my_a2a_common.constants import JSON_MEDIA_TYPE

# Skill identifiers
FIND_PRODUCT_SKILL_ID = "salesperson.find-product"
CALC_SHIPPING_SKILL_ID = "salesperson.calc-shipping"
SEARCH_DOCUMENTS_SKILL_ID = "salesperson.search-documents"
CREATE_PAYMENT_SKILL_ID = "salesperson.create-payment"
QUERY_PAYMENT_STATUS_SKILL_ID = "salesperson.query-payment-status"
GET_ORDER_STATUS_SKILL_ID = "salesperson.get-order-status"

COMMON_MODES = [JSON_MEDIA_TYPE]


FIND_PRODUCT_SKILL = AgentSkill(
    id=FIND_PRODUCT_SKILL_ID,
    name="Find Product",
    description="Search and find products by SKU or name.",
    tags=["product", "search", "catalog"],
    input_modes=COMMON_MODES,
    output_modes=COMMON_MODES,
    examples=[
        "Find product with SKU ABC123",
        "Search for laptop products",
    ],
)

CALC_SHIPPING_SKILL = AgentSkill(
    id=CALC_SHIPPING_SKILL_ID,
    name="Calculate Shipping",
    description="Calculate shipping cost for products to a destination.",
    tags=["shipping", "delivery", "cost"],
    input_modes=COMMON_MODES,
    output_modes=COMMON_MODES,
    examples=[
        "Calculate shipping for 2 items to Hanoi",
        "How much to ship this product to HCMC?",
    ],
)

SEARCH_DOCUMENTS_SKILL = AgentSkill(
    id=SEARCH_DOCUMENTS_SKILL_ID,
    name="Search Product Documents",
    description="Search product documentation, manuals, and specifications.",
    tags=["documents", "search", "knowledge"],
    input_modes=COMMON_MODES,
    output_modes=COMMON_MODES,
    examples=[
        "Find warranty information for product X",
        "Search for installation guide",
    ],
)

CREATE_PAYMENT_SKILL = AgentSkill(
    id=CREATE_PAYMENT_SKILL_ID,
    name="Create Payment Order",
    description="Create a payment order for checkout (delegates to Payment Agent).",
    tags=["payment", "checkout", "order"],
    input_modes=COMMON_MODES,
    output_modes=COMMON_MODES,
    examples=[
        "Create payment for my cart",
        "Checkout with VNPay",
    ],
)

QUERY_PAYMENT_STATUS_SKILL = AgentSkill(
    id=QUERY_PAYMENT_STATUS_SKILL_ID,
    name="Query Payment Status",
    description="Check the status of a payment order.",
    tags=["payment", "status", "query"],
    input_modes=COMMON_MODES,
    output_modes=COMMON_MODES,
    examples=[
        "Check payment status for order 12345",
        "Is my payment complete?",
    ],
)

GET_ORDER_STATUS_SKILL = AgentSkill(
    id=GET_ORDER_STATUS_SKILL_ID,
    name="Get Order Status",
    description="Get the current status of an order.",
    tags=["order", "status", "tracking"],
    input_modes=COMMON_MODES,
    output_modes=COMMON_MODES,
    examples=[
        "What's the status of my order?",
        "Track order 12345",
    ],
)

# All skills for the salesperson agent
SALESPERSON_SKILLS = [
    FIND_PRODUCT_SKILL,
    CALC_SHIPPING_SKILL,
    SEARCH_DOCUMENTS_SKILL,
    CREATE_PAYMENT_SKILL,
    QUERY_PAYMENT_STATUS_SKILL,
    GET_ORDER_STATUS_SKILL,
]
