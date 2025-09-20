import json
from utils.status import Status


class ResponseFormat:
    def __init__(self, status: Status = Status.SUCCESS, message: str = "SUCCESS", data: any = None):
        self.status = status
        self.message = message
        self.data = data

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "message": self.message,
            "data": self.data
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())