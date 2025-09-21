"""HTTP controller for the shopping session service."""

from __future__ import annotations

import asyncio
import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Type
from urllib.parse import urlsplit

from utils.app_string import INVALID_JSON_BODY
from utils.response_format import ResponseFormat
from utils.status import Status

from .service import ShoppingService

logger = logging.getLogger(__name__)


class ShoppingRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler delegating requests to :class:`ShoppingService`."""

    service = ShoppingService()

    def do_GET(self) -> None:  # noqa: N802
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

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
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


def create_http_server(host: str, port: int, service: ShoppingService | None = None) -> ThreadingHTTPServer:
    """Create a :class:`ThreadingHTTPServer` wired to the shopping service."""

    handler_cls: Type[ShoppingRequestHandler]
    if service is None:
        handler_cls = ShoppingRequestHandler
    else:
        class CustomShoppingHandler(ShoppingRequestHandler):
            service = service

        handler_cls = CustomShoppingHandler

    return ThreadingHTTPServer((host, port), handler_cls)


__all__ = ["ShoppingRequestHandler", "create_http_server"]
