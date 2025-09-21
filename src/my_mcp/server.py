"""FastAPI application exposing MCP tools over HTTP and SSE."""

from __future__ import annotations

from fastapi import FastAPI

from my_mcp.urls import router


def create_app() -> FastAPI:
    """Instantiate the FastAPI application."""

    app = FastAPI(title="MCP Tool Server", version="0.1.0")
    app.include_router(router)
    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    from config import MCP_SERVER_HOST, MCP_SERVER_PORT
    import uvicorn

    uvicorn.run(
        "my_mcp.server:app",
        host=MCP_SERVER_HOST,
        port=MCP_SERVER_PORT,
        reload=False,
    )
