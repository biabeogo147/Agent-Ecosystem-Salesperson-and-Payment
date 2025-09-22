from google.adk.a2a.utils.agent_to_a2a import to_a2a

from my_agent.payment_agent.agent import root_agent

# Turn agent into an A2A app; ADK will auto-generate agent-card at /.well-known/agent-card.json
a2a_app = to_a2a(root_agent, port=8081)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("my_agent.payment_agent.a2a_app:a2a_app", host="0.0.0.0", port=8081)