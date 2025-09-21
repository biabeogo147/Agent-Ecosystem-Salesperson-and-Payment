"""Lightweight implementation of an Agent-to-Agent (A2A) protocol."""

from __future__ import annotations

from collections import deque
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, replace
import inspect
from typing import Any

A2AHandler = Callable[["A2AMessage", Sequence["A2AMessage"]], Awaitable[Any] | Any]


@dataclass(frozen=True)
class A2AMessage:
    """A single message exchanged between two agents."""

    sender: str
    content: Any
    recipient: str | None = None
    metadata: Mapping[str, Any] | None = None


@dataclass
class A2AEndpoint:
    """Wraps a callable that can process A2A messages."""

    name: str
    handler: A2AHandler

    async def handle(self, message: A2AMessage, history: Sequence[A2AMessage]) -> Any:
        """Invoke the underlying handler while supporting sync/async callables."""

        result = self.handler(message, history)
        if inspect.isawaitable(result):
            result = await result
        return result


class A2AProtocol:
    """Dispatcher that routes messages among registered agent endpoints."""

    def __init__(self):
        self._endpoints: dict[str, A2AEndpoint] = {}
        self._history: list[A2AMessage] = []

    def register(self, endpoint: A2AEndpoint) -> None:
        """Register a new endpoint with the protocol."""

        if endpoint.name in self._endpoints:
            raise ValueError(f"Endpoint '{endpoint.name}' already registered")
        self._endpoints[endpoint.name] = endpoint

    @property
    def history(self) -> Sequence[A2AMessage]:
        """Return an immutable view of the conversation history."""

        return tuple(self._history)

    @property
    def participants(self) -> Sequence[str]:
        """Return the names of all registered endpoints."""

        return tuple(self._endpoints.keys())

    async def send(self, message: A2AMessage) -> list[A2AMessage]:
        """Send a message and propagate responses until no new messages appear."""

        if message.sender not in self._endpoints:
            raise ValueError(f"Unknown sender '{message.sender}'")
        if message.recipient and message.recipient not in self._endpoints:
            raise ValueError(f"Unknown recipient '{message.recipient}'")

        produced: list[A2AMessage] = []
        queue: deque[A2AMessage] = deque([message])

        while queue:
            current = queue.popleft()
            self._history.append(current)

            recipients = self._resolve_recipients(current)
            default_recipient = current.sender if recipients else None

            for recipient in recipients:
                endpoint = self._endpoints[recipient]
                raw_response = await endpoint.handle(current, self.history)
                responses = self._normalize_responses(raw_response, recipient, default_recipient)
                for response in responses:
                    produced.append(response)
                    queue.append(response)

        return produced

    def _resolve_recipients(self, message: A2AMessage) -> list[str]:
        if message.recipient:
            return [message.recipient]
        return [name for name in self._endpoints if name != message.sender]

    def _normalize_responses(
        self,
        raw: Any,
        sender: str,
        default_recipient: str | None,
    ) -> list[A2AMessage]:
        if raw is None:
            return []

        if isinstance(raw, A2AMessage):
            msg = raw
            if msg.sender != sender:
                msg = replace(msg, sender=sender)
            if msg.recipient is None and default_recipient is not None:
                msg = replace(msg, recipient=default_recipient)
            return [msg]

        if isinstance(raw, (str, bytes)):
            return [A2AMessage(sender=sender, content=raw, recipient=default_recipient)]

        if isinstance(raw, Mapping):
            mapping = dict(raw)
            metadata = mapping.pop("metadata", None)
            recipient = mapping.pop("recipient", default_recipient)
            return [
                A2AMessage(
                    sender=sender,
                    content=mapping,
                    recipient=recipient,
                    metadata=metadata,
                )
            ]

        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
            messages: list[A2AMessage] = []
            for item in raw:
                messages.extend(self._normalize_responses(item, sender, default_recipient))
            return messages

        return [A2AMessage(sender=sender, content=raw, recipient=default_recipient)]
