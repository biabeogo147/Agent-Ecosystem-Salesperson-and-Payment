@echo off
CALL ".venv\Scripts\activate.bat"

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

echo Starting ADK Web UI...
start cmd /k "adk web ./src/my_agent"

echo All services launched!
