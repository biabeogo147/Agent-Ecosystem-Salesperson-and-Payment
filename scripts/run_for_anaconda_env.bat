@echo off
SET ENV_NAME=Shopping-Agent-and-Merchant-Agent-with-Payment-System

CALL "D:\Anaconda\Scripts\activate.bat" %ENV_NAME%

echo Starting Salesperson MCP Server...
start cmd /k "python -m src.my_mcp.salesperson.server_salesperson_tool"

echo Starting Payment MCP Server...
start cmd /k "python -m src.my_mcp.payment.server_payment_tool"

echo Starting Payment A2A Agent...
start cmd /k "python -m src.my_agent.payment_agent.payment_a2a.payment_agent_app"

echo Starting Callback Service...
start cmd /k "python -m src.payment_callback.callback_app"

echo Starting Webhook Service...
start cmd /k "python -m src.web_hook.webhook_app"

@REM echo Starting ADK Web UI...
@REM start cmd /k "adk web ./src/my_agent"

echo Starting Salesperson Agent App...
start cmd /k "python -m src.my_agent.salesperson_agent.salesperson_agent_app"

echo Starting Websocket Server...
start cmd /k "python -m src.websocket_server.app"

echo Starting Chat UI...
start cmd /k "python -m src.chat_ui.chat_app"

echo All services launched!