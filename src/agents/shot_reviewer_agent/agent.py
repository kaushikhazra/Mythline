import os

from dotenv import load_dotenv

from pydantic_ai import Agent
from pydantic_ai.mcp import load_mcp_servers

from src.libs.utils.prompt_loader import load_system_prompt
from src.libs.utils.config_loader import load_mcp_config
from src.agents.story_creator_agent.models.state_models import Review


load_dotenv()

class ShotReviewerAgent:
    AGENT_ID = "shot_reviewer"

    def __init__(self):
        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        servers = load_mcp_servers(load_mcp_config(__file__))

        self.agent = Agent(
            llm_model,
            output_type=Review,
            system_prompt=system_prompt,
            toolsets=servers
        )

    async def run(self, prompt: str) -> Review:
        result = await self.agent.run(prompt)
        return result.output
