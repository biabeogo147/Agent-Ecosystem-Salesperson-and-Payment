from utils.status import Status


class ResponseFormat:
    def __init__(self, status: Status = Status.SUCCESS, message: str = "SUCCESS", data: any = None):
        self.status = status
        self.message = message
        self.data = data

    def to_json(self) -> dict:
        return {
            "status": self.status.value,
            "message": self.message,
            "data": self.data
        }