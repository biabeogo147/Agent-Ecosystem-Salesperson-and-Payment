import json
from starlette.responses import Response, JSONResponse


class RequestFormatJSONRPC:
    def __init__(
            self,
            jsonrpc: str = "2.0",
            id: str = None,
            method: str = "message.send",
            params: dict | None = None,
    ):
        self.jsonrpc = jsonrpc
        self.id = id
        self.method = method
        self.params = params or {}

    def to_dict(self) -> dict:
        return {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": self.method,
            "params": self.params,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_response(self) -> Response:
        return JSONResponse(content=self.to_dict())