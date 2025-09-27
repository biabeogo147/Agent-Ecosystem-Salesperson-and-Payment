import json
from utils.status import Status
from starlette.responses import Response, JSONResponse

class ResponseFormatJSONRPC:
    def __init__(
            self,
            jsonrpc: str = "2.0",
            id: str = None,
            status: Status = Status.SUCCESS,
            message: str = "SUCCESS",
            data: any = None
    ):
        self.jsonrpc = jsonrpc
        self.id = id
        self.status = status
        self.message = message
        self.data = data

    def to_dict(self) -> dict:
        base = {
            "jsonrpc": self.jsonrpc,
            "id": self.id
        }
        if self.status == Status.SUCCESS:
            base["result"] = self.data
        else:
            base["error"] = {
                "code": self.status.value,
                "message": self.message,
                "data": self.data,
            }
        return base

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_response(self) -> Response:
        return JSONResponse(content=self.to_dict())