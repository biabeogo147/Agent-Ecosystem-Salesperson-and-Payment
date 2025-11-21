from google.adk.agents import Agent, LlmAgent
from google.adk.models.lite_llm import LiteLlm

from src.config import *
from src.my_agent.salesperson_agent.salesperson_a2a.salesperson_a2a_client import create_payment_order_tool, \
    query_payment_order_status_tool
from src.my_agent.salesperson_agent.salesperson_mcp_client import prepare_find_product_tool, prepare_calc_shipping_tool, \
    prepare_reserve_stock_tool

instruction_path = os.path.join(os.path.dirname(__file__), "instruction.txt")
with open(instruction_path, "r", encoding="utf-8") as f:
    _INSTRUCTION = f.read().strip()
_DESCRIPTION = "Salesperson who helps Customers to find products, calculate shipping costs and reserve stock."


def gemini_salesperson_agent() -> Agent:
    return Agent(
        name="salesperson_agent",
        model=MODEL_NAME,
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
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
        tools=[
            prepare_find_product_tool,
            prepare_calc_shipping_tool,
            prepare_reserve_stock_tool,
            create_payment_order_tool,
            query_payment_order_status_tool,
        ],
    )


root_agent = llm_salesperson_agent() if IS_LLM_AGENT else gemini_salesperson_agent()