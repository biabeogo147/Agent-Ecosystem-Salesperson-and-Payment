import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI
from starlette.routing import Mount
from starlette.types import Scope, Receive, Send

from mcp import types as mcp_types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from src.config import *
from src.my_mcp.salesperson.tools_for_salesperson_agent import *
from src.my_mcp.logging_middleware import LoggingMiddleware, get_logger
from src.my_mcp.utils import list_mcp_tools_with_dict, call_mcp_tool_with_dict

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

@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with session_manager.run():
        yield

app = FastAPI(title="Salesperson MCP", lifespan=lifespan)
app.routes.append(Mount("/mcp", app=handle_streamable_http))
app.add_middleware(LoggingMiddleware, logger=get_logger("salesperson_agent", "salesperson_mcp_tool.log"))


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