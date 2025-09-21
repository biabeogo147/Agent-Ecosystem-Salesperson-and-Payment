import json
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("mcp_server.log")
    ]
)
logger = logging.getLogger("mcp_server")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        client_port = request.client.port if request.client else "unknown"

        method = request.method
        url = str(request.url)
        headers = dict(request.headers)

        if "authorization" in headers:
            headers["authorization"] = "Bearer [masked]"

        body, query_params = None, None
        if request.method == "POST":
            try:
                body = await request.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON body: {str(e)}. Raw body might not be JSON.")
            except Exception as e:
                logger.error(f"Error reading body: {str(e)}")
        else:
            query_params = dict(request.query_params)

        log_msg = (
            f"IP: {client_ip}:{client_port}, "
            f"URL: {url}, "
            f"Method: {method}, "
            f"Headers: {json.dumps(headers, indent=2)}, " 
            f"Body: {json.dumps(body, indent=2)}, " if body is not None else ""
            f"Query Params: {query_params}, " if query_params is not None else ""
        )

        response = await call_next(request)

        logger.debug(f"Request Detail: {log_msg}")
        logger.info(f"Response sent: status={response.status_code}")

        return response