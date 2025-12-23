import os

from dotenv import load_dotenv

from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_system_prompt
from src.agents.youtube_metadata_agent.models.output_models import YouTubeMetadata

load_dotenv()


class YouTubeMetadataAgent:
    AGENT_ID = "youtube_metadata"

    def __init__(self):
        llm_model = f"openrouter:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            output_type=YouTubeMetadata,
            system_prompt=system_prompt
        )

    async def run(self, story_json: str) -> AgentRunResult[YouTubeMetadata]:
        agent_output = await self.agent.run(story_json)
        return agent_output
