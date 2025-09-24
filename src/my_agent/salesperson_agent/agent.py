import os

from google.adk.agents import Agent, LlmAgent
from google.adk.models.lite_llm import LiteLlm

from config import *

from .skills import *
from my_mcp.mcp_toolset import get_mcp_toolset
from my_agent.salesperson_agent.remote_agent import get_payment_remote

instruction_path = os.path.join(os.path.dirname(__file__), "instruction.txt")
with open(instruction_path, "r", encoding="utf-8") as f:
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
        sub_agents=[get_payment_remote()],
        tools=[
            get_mcp_toolset(mcp_streamable_http_url),
            generate_correlation_id_tool,
            generate_return_url_tool,
            generate_cancel_url_tool,
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
            get_mcp_toolset(mcp_streamable_http_url),
            generate_correlation_id_tool,
            generate_return_url_tool,
            generate_cancel_url_tool,
        ],
    )


root_agent = gemini_salesperson_agent()