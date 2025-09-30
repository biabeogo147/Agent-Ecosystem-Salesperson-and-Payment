dir

@echo "---Activate .venv---"
call .venv\Scripts\activate.bat

@echo "---Run necessary services---"
start python src/my_mcp/salesperson/server_salesperson_tool.py
start adk web .\src\my_agent 
start python .\src\my_agent\payment_agent\payment_a2a\a2a_app.py