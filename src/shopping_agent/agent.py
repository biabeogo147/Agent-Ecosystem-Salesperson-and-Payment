from config import *
from tools import *
from google.adk.agents import Agent, LlmAgent
from google.adk.models.lite_llm import LiteLlm

def gemini_shopping_agent() -> Agent:
    return Agent(
        name="shopping_agent",
        model="gemini-2.0-flash",
        description="Shopping helper with local catalog and shipping calculator",
        instruction="You are a shopping assistant. Help users find products and calculate shipping costs based on weight and distance.",
        tools=[find_product, calc_shipping],
    )

def llm_shopping_agent() -> LlmAgent:
    return LlmAgent(
        name="shopping_agent",
        model=LiteLlm(
            model=MODEL_NAME,
            api_base=OPENAI_API_KEY,
            api_key=OPENAI_API_BASE,
        ),
        description="Shopping helper with local catalog and shipping calculator",
        instruction="You are a shopping assistant. Help users find products and calculate shipping costs based on weight and distance.",
        tools=[find_product, calc_shipping],
    )


root_agent = gemini_shopping_agent()