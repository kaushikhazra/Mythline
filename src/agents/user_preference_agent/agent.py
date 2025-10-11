import os

from dotenv import load_dotenv

from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_agent_prompt

load_dotenv()

class UserPreferenceAgent:
    AGENT_ID = "user_preference"

    def __init__(self):
        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
        system_prompt = load_agent_prompt(__file__)

        self.agent = Agent(
            llm_model,
            system_prompt=system_prompt
        )

    def run(self, prompt: str) -> AgentRunResult:
        agent_output = self.agent.run_sync(prompt)
        return agent_output
