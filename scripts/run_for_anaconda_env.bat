@echo off
SET ENV_NAME=Shopping-Agent-and-Merchant-Agent-with-Payment-System

REM >>> ĐƯỜNG DẪN TỚI activate.bat <<<
CALL "D:\Anaconda\Scripts\activate.bat" %ENV_NAME%

echo Starting Salesperson MCP Server...
start cmd /k "python -m src.my_mcp.salesperson.server_salesperson_tool"

echo Starting Payment MCP Server...
start cmd /k "python -m src.my_mcp.payment.server_payment_tool"

echo Starting Payment A2A Agent...
start cmd /k "python -m src.my_agent.payment_agent.payment_a2a.a2a_app"

echo Starting Callback Service...
start cmd /k "python -m src.payment_callback.callback_app"

echo Starting Webhook Service...
start cmd /k "python -m src.web_hook.webhook_app"

echo Starting ADK Web UI...
start cmd /k "adk web ./src/my_agent"

echo All services launched!