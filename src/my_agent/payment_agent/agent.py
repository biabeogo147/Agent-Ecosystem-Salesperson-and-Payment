from google.adk.agents import Agent, LlmAgent
from google.adk.models.lite_llm import LiteLlm

from src.config import *
from src.my_agent.payment_agent.payment_mcp_client import create_order_tool, query_order_status_tool

instruction_path = os.path.join(os.path.dirname(__file__), "instruction.txt")
with open(instruction_path, "r", encoding="utf-8") as f:
    _INSTRUCTION = f.read().strip()
_DESCRIPTION = "Payment Agent: check data, decide next_action, basic fraud prevention."

mcp_sse_url = f"http://{MCP_SERVER_HOST_PAYMENT}:{MCP_SERVER_PORT_PAYMENT}/sse"
mcp_streamable_http_url = f"http://{MCP_SERVER_HOST_PAYMENT}:{MCP_SERVER_PORT_PAYMENT}/mcp"


def gemini_payment_agent() -> Agent:
    return Agent(
        name="payment_agent",
        model=MODEL_NAME,
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        tools=[
            create_order_tool,
            query_order_status_tool,
        ]
    )


def llm_payment_agent() -> LlmAgent:
    return LlmAgent(
        name="payment_agent",
        model=LiteLlm(
            model=MODEL_NAME,
            api_base=OPENAI_API_BASE,
            api_key=OPENAI_API_KEY,
        ),
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        tools=[
            create_order_tool,
            query_order_status_tool,
        ]
    )


root_agent = llm_payment_agent() if IS_LLM_AGENT else gemini_payment_agent()