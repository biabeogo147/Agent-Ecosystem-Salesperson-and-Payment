import json
import logging
from typing import Optional
from fastapi import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("mcp_server.log")
    ]
)
logger = logging.getLogger("mcp_server")

MAX_LOG_BYTES = 4096

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        client_port = request.client.port if request.client else "unknown"
        method = request.method
        url = str(request.url)

        headers = dict(request.headers)
        if "authorization" in {k.lower(): k for k in headers}.keys():
            real_key = next(k for k in headers.keys() if k.lower() == "authorization")
            headers[real_key] = "Bearer [masked]"

        try:
            req_body_bytes: bytes = await request.body()
        except Exception:
            req_body_bytes = b""

        sent_once = False
        async def receive_with_body() -> Message:
            nonlocal sent_once, req_body_bytes
            if not sent_once:
                sent_once = True
                return {"type": "http.request", "body": req_body_bytes, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}

        request = Request(request.scope, receive=receive_with_body)

        body_for_log: Optional[str] = None
        query_for_log: Optional[dict] = None

        if method in {"POST", "PUT", "PATCH"} and req_body_bytes:
            try:
                parsed = json.loads(req_body_bytes.decode("utf-8", "ignore"))
                body_for_log = json.dumps(parsed, indent=2, ensure_ascii=False)
            except Exception:
                text = req_body_bytes.decode("utf-8", "ignore")
                if len(text) > MAX_LOG_BYTES:
                    text = text[:MAX_LOG_BYTES] + f"... [truncated to {MAX_LOG_BYTES} chars]"
                body_for_log = text
        else:
            if request.query_params:
                query_for_log = dict(request.query_params)

        response = await call_next(request)

        try:
            chunks = []
            read = 0
            async for section in response.body_iterator:
                if read < MAX_LOG_BYTES:
                    need = MAX_LOG_BYTES - read
                    chunks.append(section[:need])
                    read += len(section[:need])
                chunks.append(section)
            resp_body_bytes = b"".join(chunks)
        except Exception:
            resp_body_bytes = None

        if logger.isEnabledFor(logging.DEBUG):
            parts = [
                f"IP: {client_ip}:{client_port}",
                f"URL: {url}",
                f"Method: {method}",
                f"Headers: {json.dumps(headers, indent=2, ensure_ascii=False)}",
            ]
            if body_for_log is not None:
                parts.append(f"Body: {body_for_log}")
            if query_for_log is not None:
                parts.append(f"Query Params: {query_for_log}")

            logger.debug("Request Detail:\n" + ", ".join(parts) + "\n")

        logger.info(f"Response sent: status={response.status_code}")

        if logger.isEnabledFor(logging.DEBUG) and resp_body_bytes is not None:
            log_bytes = resp_body_bytes[:MAX_LOG_BYTES]
            truncated = len(resp_body_bytes) > MAX_LOG_BYTES
            try:
                parsed = json.loads(log_bytes.decode("utf-8", "ignore"))
                resp_log = json.dumps(parsed, indent=2, ensure_ascii=False)
            except Exception:
                resp_log = log_bytes.decode("utf-8", "ignore")
            if truncated:
                resp_log += f"\n...[truncated to {MAX_LOG_BYTES} bytes for logging]"

            resp_headers = dict(response.headers)
            if "set-cookie" in {k.lower(): k for k in resp_headers}.keys():
                real_key = next(k for k in resp_headers.keys() if k.lower() == "set-cookie")
                resp_headers[real_key] = "[masked]"

            logger.debug(
                "Response Detail:\n"
                f"status={response.status_code}\n"
                f"headers={resp_headers}\n"
                f"body={resp_log}\n"
            )

        if resp_body_bytes is not None:
            new_response = Response(
                content=resp_body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=getattr(response, "media_type", None),
                background=getattr(response, "background", None),
            )
            return new_response

        return response
