"""Definitions for the shopping (customer) agent."""

from google.adk.agents import Agent, LlmAgent
from google.adk.models.lite_llm import LiteLlm

from config import *

with open("src/shopping_agent/instruction.txt", "r") as f:
    _INSTRUCTION = f.read().strip()

_DESCRIPTION = "Customer who evaluates merchant proposals, tracks costs, and confirms purchases."


def gemini_shopping_agent() -> Agent:
    """Instantiate the Gemini-based shopping agent."""

    return Agent(
        name="shopping_agent",
        model="gemini-2.0-flash",
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
    )


def llm_shopping_agent() -> LlmAgent:
    """Instantiate the OpenAI-compatible shopping agent."""

    return LlmAgent(
        name="shopping_agent",
        model=LiteLlm(
            model=MODEL_NAME,
            api_base=OPENAI_API_KEY,
            api_key=OPENAI_API_BASE,
        ),
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
    )


root_agent = gemini_shopping_agent()
