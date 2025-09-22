from google.adk.agents import Agent, LlmAgent
from google.adk.models.lite_llm import LiteLlm

from config import *
from my_mcp.mcp_toolset import get_mcp_toolset

instruction_path = os.path.join(os.path.dirname(__file__), "instruction.txt")
with open(instruction_path, "r") as f:
    _INSTRUCTION = f.read().strip()
_DESCRIPTION = "Payment Agent: check data, decide next_action, basic fraud prevention."

mcp_sse_url = f"http://{MCP_SERVER_HOST_PAYMENT}:{MCP_SERVER_PORT_PAYMENT}/sse"
mcp_streamable_http_url = f"http://{MCP_SERVER_HOST_PAYMENT}:{MCP_SERVER_PORT_PAYMENT}/mcp"


def gemini_payment_agent() -> Agent:
    return Agent(
        name="payment_agent",
        model="gemini-2.0-flash",
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        tools=[get_mcp_toolset(mcp_streamable_http_url)]
    )


def llm_payment_agent() -> LlmAgent:
    return LlmAgent(
        name="payment_agent",
        model=LiteLlm(
            model=MODEL_NAME,
            api_base=OPENAI_API_KEY,
            api_key=OPENAI_API_BASE,
        ),
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        tools=[get_mcp_toolset(mcp_streamable_http_url)]
    )


root_agent = gemini_payment_agent()