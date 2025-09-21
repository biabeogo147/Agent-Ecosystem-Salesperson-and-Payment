"""Runtime helper for launching the shopping session HTTP controller."""

from __future__ import annotations

import logging
import os

from .controller import create_http_server

logger = logging.getLogger(__name__)


def _load_config() -> tuple[str, int]:
    host = os.environ.get("SHOP_API_HOST", "0.0.0.0")
    port = int(os.environ.get("SHOP_API_PORT", "8080"))
    return host, port


def run() -> None:  # pragma: no cover - exercised via deployment
    host, port = _load_config()
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    with create_http_server(host, port) as httpd:
        logger.info("Starting shopping session API on %s:%s", host, port)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:  # pragma: no cover
            logger.info("Shutting down shopping session API")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    run()


__all__ = ["run"]
