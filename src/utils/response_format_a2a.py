import json
from utils.status import Status
from starlette.responses import Response, JSONResponse


class ResponseFormatA2A:
    def __init__(
            self,
            jsonrpc: str = "2.0",
            request_id: str = None,
            status: Status = Status.SUCCESS,
            message: str = "SUCCESS",
            data: any = None
    ):
        self.jsonrpc = jsonrpc
        self.request_id = request_id
        self.status = status
        self.message = message
        self.data = data

    def to_dict(self) -> dict:
        return {
            "jsonrpc": self.jsonrpc,
            "request_id": self.request_id,
            "status": self.status.value,
            "message": self.message,
            "data": self.data
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_response(self) -> Response:
        return JSONResponse(content=self.to_dict())