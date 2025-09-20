import sys

from mcp import StdioServerParameters

from google.adk.tools import MCPToolset
from google.adk.tools.mcp_tool import StdioConnectionParams
from google.adk.agents import Agent, LlmAgent
from google.adk.models.lite_llm import LiteLlm

from config import *
from my_mcp import PATH_TO_MCP_SERVER

with open("src/shopping_agent/instruction.txt", "r") as f:
    _INSTRUCTION = f.read().strip()
_DESCRIPTION = "Shopping helper finding products, shipping calculator and reserving stock"


def get_mcp_toolset() -> MCPToolset:
    """Get MCP Toolset"""
    py_cmd = sys.executable or ("python3" if os.name != "nt" else "python")

    if not PATH_TO_MCP_SERVER.exists():
        raise FileNotFoundError(f"MCP server script not found: {PATH_TO_MCP_SERVER}")

    # env = os.environ.copy()
    cwd = str(PATH_TO_MCP_SERVER.parent)

    return MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=py_cmd,
                args=[str(PATH_TO_MCP_SERVER)],
                # env=env,
                cwd=cwd,
                # startup_timeout_seconds=15,
                # healthcheck_command=None,  # hoặc ["python","-V"] nếu SDK hỗ trợ
            )
        )
    )


def gemini_shopping_agent() -> Agent:
    return Agent(
        name="shopping_agent",
        model="gemini-2.0-flash",
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        tools=[get_mcp_toolset()],
    )


def llm_shopping_agent() -> LlmAgent:
    return LlmAgent(
        name="shopping_agent",
        model=LiteLlm(
            model=MODEL_NAME,
            api_base=OPENAI_API_KEY,
            api_key=OPENAI_API_BASE,
        ),
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        tools=[get_mcp_toolset()],
    )


root_agent = gemini_shopping_agent()