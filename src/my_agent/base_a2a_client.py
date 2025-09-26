"""Shared helpers for calling remote A2A agents over HTTP.

The salesperson agent – and any future collaborators – talk to remote agents
exposed through the A2A HTTP interface.  Each bespoke client previously had to
open HTTP connections, deal with authentication headers, and validate the
`ResponseFormat` envelope by hand.  This module centralises those mechanics so
individual agent clients can stay focused on domain-specific payload shaping.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

import httpx

from utils.response_format import ResponseFormat
from utils.status import Status


class BaseA2AClient:
    """Base helper that wraps :class:`httpx.AsyncClient` interactions."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str | None = None,
        timeout: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("base_url must be provided for A2A calls")

        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "BaseA2AClient":
        await self._ensure_client()
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTP client when owned by this instance."""

        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Return an :class:`httpx.AsyncClient`, constructing it if needed."""

        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self._timeout),
            )
            self._owns_client = True
        return self._client

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_payload: Mapping[str, Any] | None = None,
    ) -> Any:
        """Execute an HTTP request and decode the JSON body."""

        client = await self._ensure_client()
        try:
            response = await client.request(
                method,
                path,
                json=json_payload,
                headers=self._build_headers(),
            )
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"A2A {method} request to '{path}' failed: {exc}" 
            ) from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            text_snippet = exc.response.text[:200]
            raise RuntimeError(
                f"A2A endpoint '{path}' returned HTTP {exc.response.status_code}: {text_snippet}"
            ) from exc

        try:
            return response.json()
        except json.JSONDecodeError as exc:
            snippet = response.text[:200]
            raise RuntimeError(
                f"A2A endpoint '{path}' returned non-JSON content: {snippet}"
            ) from exc

    async def _post_json(
        self,
        path: str,
        payload: Mapping[str, Any],
    ) -> Any:
        """Convenience wrapper for POST requests returning JSON."""

        return await self._request_json("POST", path, json_payload=payload)

    @staticmethod
    def _ensure_response_format(payload: Any, *, operation: str) -> ResponseFormat:
        """Validate and convert responses into :class:`ResponseFormat`."""

        try:
            return ResponseFormat.from_dict(payload)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                f"A2A operation '{operation}' returned an unexpected payload: {payload!r}"
            ) from exc

    @classmethod
    def _extract_success_data(cls, payload: Any, *, operation: str) -> Any:
        """Return the ``data`` field when the ResponseFormat indicates success."""

        response = cls._ensure_response_format(payload, operation=operation)
        if response.status is not Status.SUCCESS:
            raise RuntimeError(
                f"A2A operation '{operation}' returned status '{response.status.value}': {response.message}"
            )
        return response.data


__all__ = ["BaseA2AClient"]

