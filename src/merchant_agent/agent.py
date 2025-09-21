"""Merchant agent definitions that integrate with a remote MCP service."""

from __future__ import annotations

import inspect
import os
from typing import TYPE_CHECKING, Any, Callable
from urllib.parse import urlparse, urlunparse

from config import MODEL_NAME, OPENAI_API_BASE, OPENAI_API_KEY

try:  
    from google.adk.tools import MCPToolset as _GoogleMCPToolset
except ImportError:  
    _GoogleMCPToolset = None

try:  
    from google.adk.tools.mcp_tool import StreamableHTTPConnectionParams as _StreamableHTTPConnectionParams
except ImportError:  
    _StreamableHTTPConnectionParams = None

try:  
    from google.adk.tools.mcp_tool import HttpConnectionParams as _HttpConnectionParams
except ImportError:  
    _HttpConnectionParams = None

try:  
    from google.adk.agents import Agent as _GoogleAgent, LlmAgent as _GoogleLlmAgent
except ImportError:  
    _GoogleAgent = None
    _GoogleLlmAgent = None

try:  
    from google.adk.models.lite_llm import LiteLlm as _GoogleLiteLlm
except ImportError:  
    _GoogleLiteLlm = None

if TYPE_CHECKING:
    from google.adk.agents import Agent, LlmAgent
    from google.adk.models.lite_llm import LiteLlm
    from google.adk.tools import MCPToolset

_MCP_SERVICE_URL_ENV = "MCP_SERVICE_URL"
_DEFAULT_MCP_SERVICE_URL = "http://localhost:8000"

with open("src/merchant_agent/instruction.txt", "r", encoding="utf-8") as f:
    _INSTRUCTION = f.read().strip()

_DESCRIPTION = "Salesperson who helps Customers to find products, calculate shipping costs and reserve stock."


def _require(name: str, value: Any) -> Any:
    """Ensure optional Google ADK components are available before use."""

    if value is None:
        raise RuntimeError(
            "google-adk is required to instantiate merchant agents with MCP tooling; "
            f"missing component: {name}."
        )
    return value


def _resolve_http_connection_class() -> Callable[..., Any]:
    """Return the first available HTTP connection parameter class."""

    for candidate, name in (
        (_StreamableHTTPConnectionParams, "StreamableHTTPConnectionParams"),
        (_HttpConnectionParams, "HttpConnectionParams"),
    ):
        if candidate is not None:
            return candidate
    raise RuntimeError(
        "google-adk does not provide HTTP MCP connection parameters. "
        "Install a version that supports StreamableHTTP transports."
    )


def _normalise_service_url(raw_url: str | None) -> str:
    """Normalise the MCP service URL and validate its scheme."""

    candidate = (raw_url or _DEFAULT_MCP_SERVICE_URL).strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(
            "MCP service URL must use http or https scheme: "
            f"{candidate!r}"
        )
    if not parsed.netloc:
        raise ValueError(f"MCP service URL is missing host information: {candidate!r}")

    path = parsed.path.rstrip("/")
    normalised = urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))
    return normalised


def _build_websocket_url(http_url: str) -> str:
    """Derive a WebSocket URL from the HTTP endpoint if required."""

    parsed = urlparse(http_url)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunparse((ws_scheme, parsed.netloc, parsed.path, "", "", ""))


def _create_http_connection_params(service_url: str) -> Any:
    """Instantiate the ADK connection parameter object for HTTP transport."""

    connection_cls = _resolve_http_connection_class()
    signature = inspect.signature(connection_cls)
    kwargs: dict[str, Any] = {}

    for option in ("url", "endpoint", "base_url", "uri"):
        if option in signature.parameters:
            kwargs[option] = service_url
            break
    else:
        raise RuntimeError(
            "Unsupported google-adk HTTP connection parameter signature; cannot determine URL argument."
        )

    for ws_option in ("websocket_url", "ws_url"):
        parameter = signature.parameters.get(ws_option)
        if parameter is not None and parameter.default is inspect._empty:
            kwargs[ws_option] = _build_websocket_url(service_url)

    return connection_cls(**kwargs)


def get_mcp_toolset() -> "MCPToolset":
    """Create an MCP toolset that connects to a remote HTTP MCP server."""

    toolset_cls = _require("MCPToolset", _GoogleMCPToolset)
    service_url = _normalise_service_url(os.environ.get(_MCP_SERVICE_URL_ENV))
    connection_params = _create_http_connection_params(service_url)
    return toolset_cls(connection_params=connection_params)


def gemini_merchant_agent() -> "Agent":
    """Instantiate the Gemini-based merchant agent configured for remote MCP."""

    agent_cls = _require("Agent", _GoogleAgent)
    return agent_cls(
        name="merchant_agent",
        model="gemini-2.0-flash",
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        tools=[get_mcp_toolset()],
    )


def llm_merchant_agent() -> "LlmAgent":
    """Instantiate the OpenAI-compatible merchant agent configured for remote MCP."""

    agent_cls = _require("LlmAgent", _GoogleLlmAgent)
    lite_llm_cls = _require("LiteLlm", _GoogleLiteLlm)
    return agent_cls(
        name="merchant_agent",
        model=lite_llm_cls(
            model=MODEL_NAME,
            api_base=OPENAI_API_KEY,
            api_key=OPENAI_API_BASE,
        ),
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        tools=[get_mcp_toolset()],
    )


try:
    root_agent = gemini_merchant_agent()
except RuntimeError:  
    root_agent = None