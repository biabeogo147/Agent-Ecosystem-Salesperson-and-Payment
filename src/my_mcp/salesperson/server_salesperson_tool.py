import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI
from mcp import types as mcp_types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Mount
from starlette.types import Scope, Receive, Send

from src.config import *
from src.data.elasticsearch.index import create_products_index, index_exists
from src.data.elasticsearch.sync import sync_products_to_elastic
from src.my_mcp.logging_middleware import LoggingMiddleware
from src.my_mcp.salesperson.tools_for_salesperson_agent import *
from src.my_mcp.utils import list_mcp_tools_with_dict, call_mcp_tool_with_dict
from src.utils.logger import set_app_context, AppLogger


class AppContextMiddleware(BaseHTTPMiddleware):
    """Middleware to set app logger context for all requests."""

    async def dispatch(self, request, call_next):
        with set_app_context(AppLogger.SALESPERSON_MCP):
            response = await call_next(request)
        return response

my_mcp_server = Server("salesperson_mcp")


@my_mcp_server.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    return await list_mcp_tools_with_dict(ADK_TOOLS_FOR_SALESPERSON)


@my_mcp_server.call_tool()
async def call_mcp_tool(name: str, arguments: dict | None) -> list[mcp_types.Content]:
    return await call_mcp_tool_with_dict(name, arguments, ADK_TOOLS_FOR_SALESPERSON)


session_manager = StreamableHTTPSessionManager(
    app=my_mcp_server,
    event_store=None,
    json_response=False,
    stateless=True,
)

# Use Streamable HTTP transport for /mcp endpoint
async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
    await session_manager.handle_request(scope, receive, send)


# Background task to sync products every 20 seconds
async def sync_products_periodically():
    """Background task that syncs products from DB to Elasticsearch every 20 seconds."""
    while True:
        try:
            await asyncio.sleep(20)
            # Set context for background task
            with set_app_context(AppLogger.SALESPERSON_MCP):
                salesperson_mcp_logger.info("🔄 Starting periodic product sync to Elasticsearch...")

                if not await index_exists():
                    salesperson_mcp_logger.warning("⚠️ Elasticsearch index not found. Creating index...")
                    await create_products_index()

                await sync_products_to_elastic()
                salesperson_mcp_logger.info("✅ Periodic product sync completed successfully.")
        except Exception as e:
            salesperson_mcp_logger.error(f"❌ Error during periodic sync: {str(e)}")


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    salesperson_mcp_logger.info("🚀 Starting Salesperson MCP server...")
    
    try:
        if not await index_exists():
            salesperson_mcp_logger.info("📋 Creating Elasticsearch index for products...")
            await create_products_index()
        else:
            salesperson_mcp_logger.info("✅ Elasticsearch index already exists.")
    except Exception as e:
        salesperson_mcp_logger.error(f"❌ Failed to initialize Elasticsearch index: {str(e)}")
    
    sync_task = asyncio.create_task(sync_products_periodically())
    
    async with session_manager.run():
        yield
    
    salesperson_mcp_logger.info("🛑 Shutting down Salesperson MCP server...")
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        salesperson_mcp_logger.info("✅ Background sync task cancelled successfully.")


app = FastAPI(title="Salesperson MCP", lifespan=lifespan)
app.routes.append(Mount("/mcp", app=handle_streamable_http))

# Add middlewares in reverse order (last added = first executed)
app.add_middleware(
    LoggingMiddleware,
    logger=salesperson_mcp_logger
)
app.add_middleware(AppContextMiddleware)


# Using SSE transport for /sse (GET) and /message (POST) endpoints
# app = FastAPI(title="Merchant MCP")
# app.add_middleware(LoggingMiddleware)
#
# # By default, most MCP clients expect GET /sse and POST /message for SSE transport.
# # SseServerTransport will advertise the /message URL back to the client.
# sse = SseServerTransport("/message")
#
# # POST /message (client -> server JSON-RPC)
# app.routes.append(Mount("/message", app=sse.handle_post_message))
#
# # GET /sse (server -> client event-stream)
# @app.get("/sse")
# async def sse_endpoint(request: Request):
#     async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
#         await my_mcp_server.run(
#             read_stream,
#             write_stream,
#             InitializationOptions(
#                 server_name=my_mcp_server.name,
#                 server_version="0.1.0",
#                 capabilities=my_mcp_server.get_capabilities(
#                     notification_options=NotificationOptions(),
#                     experimental_capabilities={},
#                 ),
#             ),
#         )
#     return {"status": "disconnected"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=MCP_SERVER_PORT_SALESPERSON,
        reload=False,
    )