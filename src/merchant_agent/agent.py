"""Merchant agent that communicates with the MCP service over HTTP + SSE."""

from __future__ import annotations

import asyncio
import contextlib
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx

from my_mcp import MCP_API_PREFIX, build_mcp_url

_INSTRUCTION = Path("src/merchant_agent/instruction.txt").read_text(encoding="utf-8").strip()
_DESCRIPTION = "Salesperson who helps Customers to find products, calculate shipping costs and reserve stock."

API_BASE_URL = build_mcp_url(MCP_API_PREFIX)


class McpSSEClient:
    """Minimal HTTP + SSE client for invoking MCP tools."""

    def __init__(self, *, client_id: Optional[str] = None, api_base_url: str = API_BASE_URL) -> None:
        self.client_id = client_id or uuid.uuid4().hex
        self._api_base = api_base_url if api_base_url.endswith("/") else f"{api_base_url}/"
        self._stream_url = urljoin(self._api_base, "stream")
        self._tools_url = urljoin(self._api_base, "tools")
        self._events: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._pending: List[Dict[str, Any]] = []
        self._listener: Optional[asyncio.Task[None]] = None

    async def connect(self) -> None:
        if self._listener and not self._listener.done():
            return
        self._listener = asyncio.create_task(self._listen())

    async def close(self) -> None:
        if self._listener is None:
            return
        self._listener.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._listener
        self._listener = None

    async def list_tools(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            response = await client.get(self._tools_url)
            response.raise_for_status()
            payload = response.json()
        return payload.get("tools", [])

    async def invoke_tool(self, tool_name: str, arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
        await self.connect()

        invocation_url = urljoin(self._tools_url + "/", f"{tool_name}/invoke")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                invocation_url,
                json={"client_id": self.client_id, "arguments": arguments or {}},
            )
            response.raise_for_status()
            meta = response.json()

        event_id = meta.get("event_id")
        if not event_id:
            raise RuntimeError("MCP server did not return an event_id")

        return await self._wait_for_event(event_id)

    async def call_tool(self, tool_name: str, **arguments: Any) -> Dict[str, Any]:
        return await self.invoke_tool(tool_name, arguments)

    async def _listen(self) -> None:
        params = {"client_id": self.client_id}
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", self._stream_url, params=params) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data:"):
                        data = line.removeprefix("data:").strip()
                        if not data:
                            continue
                        try:
                            payload = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        await self._events.put(payload)

    async def _wait_for_event(self, event_id: str) -> Dict[str, Any]:
        cached = self._pop_pending(event_id)
        if cached is not None:
            return cached

        while True:
            payload = await self._events.get()
            if payload.get("event_id") == event_id:
                return payload
            self._pending.append(payload)

    def _pop_pending(self, event_id: str) -> Optional[Dict[str, Any]]:
        for idx, payload in enumerate(self._pending):
            if payload.get("event_id") == event_id:
                return self._pending.pop(idx)
        return None


class MerchantAgent:
    """Simple agent facade that proxies tool calls to the MCP service."""

    def __init__(self, client: Optional[McpSSEClient] = None) -> None:
        self.name = "merchant_agent"
        self.description = _DESCRIPTION
        self.instruction = _INSTRUCTION
        self.client = client or McpSSEClient(api_base_url=API_BASE_URL)

    async def list_tools(self) -> List[Dict[str, Any]]:
        return await self.client.list_tools()

    async def call_tool(self, tool_name: str, **arguments: Any) -> Dict[str, Any]:
        event = await self.client.call_tool(tool_name, **arguments)
        if event.get("status") != "success":
            raise RuntimeError(event.get("error", "Unknown MCP error"))
        return event

    async def call_tool_and_parse(self, tool_name: str, **arguments: Any) -> Any:
        event = await self.call_tool(tool_name, **arguments)
        result = event.get("result")
        if isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return result
        return result

    def call_tool_sync(self, tool_name: str, **arguments: Any) -> Any:
        return asyncio.run(self.call_tool_and_parse(tool_name, **arguments))


root_agent = MerchantAgent()
