from google.adk.agents import Agent, LlmAgent
from google.adk.models.lite_llm import LiteLlm

from config import *
from my_agent.salesperson_agent.salesperson_a2a.remote_agent import get_payment_remote
from my_agent.salesperson_agent.salesperson_a2a.payment_tasks import prepare_create_order_payload_tool, \
    prepare_query_status_payload_tool
from my_agent.salesperson_agent.salesperson_a2a.product_tasks import prepare_reserve_stock_tool, prepare_calc_shipping_tool, \
    prepare_find_product_tool

instruction_path = os.path.join(os.path.dirname(__file__), "instruction.txt")
with open(instruction_path, "r", encoding="utf-8") as f:
    _INSTRUCTION = f.read().strip()
_DESCRIPTION = "Salesperson who helps Customers to find products, calculate shipping costs and reserve stock."


def gemini_salesperson_agent() -> Agent:
    return Agent(
        name="salesperson_agent",
        model="gemini-2.0-flash",
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        sub_agents=[get_payment_remote()],
        tools=[
            prepare_find_product_tool,
            prepare_calc_shipping_tool,
            prepare_reserve_stock_tool,
            prepare_create_order_payload_tool,
            prepare_query_status_payload_tool,
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
        sub_agents=[get_payment_remote()],
        tools=[
            prepare_find_product_tool,
            prepare_calc_shipping_tool,
            prepare_reserve_stock_tool,
            prepare_create_order_payload_tool,
            prepare_query_status_payload_tool,
        ],
    )


root_agent = gemini_salesperson_agent()
