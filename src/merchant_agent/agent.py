import sys

from mcp import StdioServerParameters

from google.adk.tools import MCPToolset
from google.adk.tools.mcp_tool import StdioConnectionParams
from google.adk.agents import Agent, LlmAgent
from google.adk.models.lite_llm import LiteLlm

from config import *
from my_mcp import PATH_TO_MCP_SERVER

with open("src/merchant_agent/instruction.txt", "r") as f:
    _INSTRUCTION = f.read().strip()
_DESCRIPTION = "Salesperson who helps Customers to find products, calculate shipping costs and reserve stock."


def get_mcp_toolset() -> MCPToolset:
    """Get MCP Toolset"""
    py_cmd = sys.executable or ("python3" if os.name != "nt" else "python")
    cwd = str(PATH_TO_MCP_SERVER.parent)

    if not PATH_TO_MCP_SERVER.exists():
        raise FileNotFoundError(f"MCP server script not found: {PATH_TO_MCP_SERVER}")


    return MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=py_cmd,
                args=[str(PATH_TO_MCP_SERVER)],
                cwd=cwd,
            )
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