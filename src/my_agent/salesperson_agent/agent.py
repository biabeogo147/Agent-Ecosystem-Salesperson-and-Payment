from google.adk.agents import Agent, LlmAgent
from google.adk.models.lite_llm import LiteLlm

from config import *
from my_mcp.mcp_toolset import get_mcp_toolset
from my_agent.salesperson_agent.payment_remote import payment_remote

instruction_path = os.path.join(os.path.dirname(__file__), "instruction.txt")
with open(instruction_path, "r") as f:
    _INSTRUCTION = f.read().strip()
_DESCRIPTION = "Salesperson who helps Customers to find products, calculate shipping costs and reserve stock."

mcp_sse_url = f"http://{MCP_SERVER_HOST_SALESPERSON}:{MCP_SERVER_PORT_SALESPERSON}/sse"
mcp_streamable_http_url = f"http://{MCP_SERVER_HOST_SALESPERSON}:{MCP_SERVER_PORT_SALESPERSON}/mcp"


def gemini_salesperson_agent() -> Agent:
    return Agent(
        name="salesperson_agent",
        model="gemini-2.0-flash",
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        sub_agents=[payment_remote],
        tools=[get_mcp_toolset(mcp_streamable_http_url)],
    )


def llm_salesperson_agent() -> LlmAgent:
    return LlmAgent(
        name="salesperson_agent",
        model=LiteLlm(
            model=MODEL_NAME,
            api_base=OPENAI_API_KEY,
            api_key=OPENAI_API_BASE,
        ),
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        sub_agents=[payment_remote],
        tools = [get_mcp_toolset(mcp_streamable_http_url)],
    )


root_agent = gemini_salesperson_agent()