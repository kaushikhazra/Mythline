import os

from dotenv import load_dotenv

from pydantic_ai import Agent
from pydantic_ai.mcp import load_mcp_servers
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_system_prompt
from src.libs.utils.config_loader import load_mcp_config

load_dotenv()

class ShotCreator:
    AGENT_ID = "shot_creator"

    def __init__(self):
        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        # servers = load_mcp_servers(load_mcp_config(__file__))

        self.messages = []

        self.agent = Agent(
            llm_model,
            system_prompt=system_prompt
            # toolsets=servers
        )

    def run(self, prompt: str) -> AgentRunResult:
        agent_output = self.agent.run_sync(prompt, message_history=self.messages)
        self.messages = agent_output.all_messages()
        return agent_output
