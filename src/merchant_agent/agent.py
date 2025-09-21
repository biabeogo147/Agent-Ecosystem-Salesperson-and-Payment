from google.adk.tools import MCPToolset
from google.adk.tools.mcp_tool import SseConnectionParams
from google.adk.agents import Agent, LlmAgent
from google.adk.models.lite_llm import LiteLlm

from config import *

with open("src/merchant_agent/instruction.txt", "r") as f:
    _INSTRUCTION = f.read().strip()
_DESCRIPTION = "Salesperson who helps Customers to find products, calculate shipping costs and reserve stock."

mcp_sse_url = f"http://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}/sse"


def get_mcp_toolset() -> MCPToolset:
    """Get MCP Toolset"""

    headers = {}
    token = os.getenv("MCP_AUTH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    return MCPToolset(
        connection_params=SseConnectionParams(
            url=mcp_sse_url,
            headers=headers or None,
            timeout=30,
            sse_read_timeout=120,
        )
    )


def gemini_merchant_agent() -> Agent:
    return Agent(
        name="merchant_agent",
        model="gemini-2.0-flash",
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        tools=[get_mcp_toolset()],
    )


def llm_merchant_agent() -> LlmAgent:
    return LlmAgent(
        name="merchant_agent",
        model=LiteLlm(
            model=MODEL_NAME,
            api_base=OPENAI_API_KEY,
            api_key=OPENAI_API_BASE,
        ),
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        tools=[get_mcp_toolset()],
    )


root_agent = gemini_merchant_agent()