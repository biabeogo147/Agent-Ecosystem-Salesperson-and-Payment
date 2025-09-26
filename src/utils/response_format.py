import json
from typing import Any, Mapping

from utils.status import Status


class ResponseFormat:
    """Simple wrapper around the API response envelope."""

    def __init__(
        self,
        status: Status = Status.SUCCESS,
        message: str = "SUCCESS",
        data: Any = None,
    ) -> None:
        self.status = status
        self.message = message
        self.data = data

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResponseFormat":
        """Build an instance from a raw mapping."""

        if not isinstance(payload, Mapping):
            raise TypeError("Response payload must be a mapping")

        missing = [key for key in ("status", "message", "data") if key not in payload]
        if missing:
            raise ValueError(f"Response payload is missing required keys: {missing}")

        try:
            status = Status(payload["status"])
        except ValueError as exc:
            raise ValueError(f"Unknown status value: {payload['status']!r}") from exc

        message_raw = payload.get("message", "")
        message = message_raw if isinstance(message_raw, str) else str(message_raw)

        return cls(status=status, message=message, data=payload.get("data"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "message": self.message,
            "data": self.data,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
