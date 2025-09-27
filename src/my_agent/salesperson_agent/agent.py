from typing import Any, Mapping, Sequence

from google.adk.agents import Agent, LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool

from config import *
from my_agent.salesperson_agent.salesperson_a2a import SalespersonA2AClient
from my_agent.salesperson_agent.salesperson_a2a.remote_agent import get_remote_payment_agent
from my_agent.salesperson_agent.salesperson_mcp_client import prepare_find_product_tool, prepare_calc_shipping_tool, \
    prepare_reserve_stock_tool

instruction_path = os.path.join(os.path.dirname(__file__), "instruction.txt")
with open(instruction_path, "r", encoding="utf-8") as f:
    _INSTRUCTION = f.read().strip()
_DESCRIPTION = "Salesperson who helps Customers to find products, calculate shipping costs and reserve stock."


async def _create_payment_order(
    items: Sequence[Any],
    customer: Any,
    channel: str,
    *,
    note: str | None = None,
    metadata: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    async with SalespersonA2AClient() as client:
        response = await client.create_order(
            items=items,
            customer=customer,
            channel=channel,
            note=note,
            metadata=dict(metadata) if metadata is not None else None,
        )
    return response.to_dict()


async def _query_payment_order_status(correlation_id: str) -> dict[str, Any]:
    async with SalespersonA2AClient() as client:
        response = await client.query_status(correlation_id)
    return response.to_dict()


create_payment_order_tool = FunctionTool(_create_payment_order)
query_payment_order_status_tool = FunctionTool(_query_payment_order_status)


def gemini_salesperson_agent() -> Agent:
    return Agent(
        name="salesperson_agent",
        model="gemini-2.0-flash",
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        sub_agents=[get_remote_payment_agent()],
        tools=[
            prepare_find_product_tool,
            prepare_calc_shipping_tool,
            prepare_reserve_stock_tool,
            create_payment_order_tool,
            query_payment_order_status_tool,
        ],
    )


def llm_salesperson_agent() -> LlmAgent:
    return LlmAgent(
        name="salesperson_agent",
        model=LiteLlm(
            model=MODEL_NAME,
            api_base=OPENAI_API_BASE,
            api_key=OPENAI_API_KEY,
        ),
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        sub_agents=[get_remote_payment_agent()],
        tools=[
            prepare_find_product_tool,
            prepare_calc_shipping_tool,
            prepare_reserve_stock_tool,
            create_payment_order_tool,
            query_payment_order_status_tool,
        ],
    )


root_agent = gemini_salesperson_agent()
