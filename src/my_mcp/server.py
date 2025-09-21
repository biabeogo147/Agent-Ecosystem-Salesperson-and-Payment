"""Executable module to run the MCP HTTP service."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

from utils.app_string import INVALID_JSON_BODY
from utils.response_format import ResponseFormat
from utils.status import Status

from .api import MCPService

logger = logging.getLogger(__name__)


class MCPRequestHandler(BaseHTTPRequestHandler):
    service = MCPService()

    def do_GET(self) -> None:  # noqa: N802 - signature imposed by BaseHTTPRequestHandler
        self._handle("GET", None)

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b""
        payload: Any | None = None
        if raw_body:
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except json.JSONDecodeError:
                body = ResponseFormat(
                    status=Status.INVALID_JSON,
                    message=INVALID_JSON_BODY,
                    data=None,
                )
                self._send_response(HTTPStatus.BAD_REQUEST, body.to_dict())
                return
        self._handle("POST", payload)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003 - method from BaseHTTPRequestHandler
        logger.info("%s - %s", self.address_string(), format % args)

    def _handle(self, method: str, payload: Any | None) -> None:
        path = urlsplit(self.path).path
        status, body = asyncio.run(self.service.dispatch(method, path, payload))
        self._send_response(status, body)

    def _send_response(self, status: int, body: Any) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _load_config() -> tuple[str, int]:
    host = os.environ.get("MCP_SERVICE_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_SERVICE_PORT", "8000"))
    return host, port


def run() -> None:
    host, port = _load_config()
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    with ThreadingHTTPServer((host, port), MCPRequestHandler) as httpd:
        logger.info("Starting MCP service on %s:%s", host, port)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:  # pragma: no cover - interactive shutdown
            logger.info("Shutting down MCP service")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    run()
