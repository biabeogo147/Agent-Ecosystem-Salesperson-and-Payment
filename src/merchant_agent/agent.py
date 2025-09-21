from urllib.parse import urlparse

from google.adk.tools import MCPToolset
from google.adk.agents import Agent, LlmAgent
from google.adk.models.lite_llm import LiteLlm

from config import *
from my_mcp.urls import MCP_WEBSOCKET_PATH

try:
    from google.adk.tools.mcp_tool import WebsocketConnectionParams
except ImportError:
    # Some versions expose the class with a capital "S" in "WebSocket".
    from google.adk.tools.mcp_tool import WebSocketConnectionParams as WebsocketConnectionParams

with open("src/merchant_agent/instruction.txt", "r") as f:
    _INSTRUCTION = f.read().strip()
_DESCRIPTION = "Salesperson who helps Customers to find products, calculate shipping costs and reserve stock."


def _build_mcp_ws_url() -> str:
    path = MCP_WEBSOCKET_PATH if MCP_WEBSOCKET_PATH.startswith("/") else f"/{MCP_WEBSOCKET_PATH}"

    raw_host = (MCP_SERVER_HOST or "").strip()
    if not raw_host:
        raw_host = "127.0.0.1"

    if raw_host.startswith(("ws://", "wss://")):
        base = raw_host.rstrip("/")
        return f"{base}{path}"

    parsed = urlparse(raw_host)
    if parsed.scheme:
        scheme = parsed.scheme if parsed.scheme in {"ws", "wss"} else "ws"
        netloc = parsed.netloc or parsed.path
        return f"{scheme}://{netloc.rstrip('/')}{path}"

    host = raw_host.rstrip("/")
    if ":" in host:
        # Host already includes a port component.
        return f"ws://{host}{path}"

    return f"ws://{host}:{MCP_SERVER_PORT}{path}"


def get_mcp_toolset() -> MCPToolset:
    """Get MCP Toolset connected to the MCP FastAPI WebSocket server."""
    ws_url = _build_mcp_ws_url()

    return MCPToolset(
        connection_params=WebsocketConnectionParams(url=ws_url)
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
