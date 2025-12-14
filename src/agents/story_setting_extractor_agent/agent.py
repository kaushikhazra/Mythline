import os

from dotenv import load_dotenv

from pydantic_ai import Agent

from src.libs.utils.prompt_loader import load_system_prompt
from src.graphs.story_research_graph.models.research_models import Setting

load_dotenv()


class StorySettingExtractorAgent:
    AGENT_ID = "story_setting_extractor"

    def __init__(self):
        llm_model = f"openrouter:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            output_type=Setting,
            system_prompt=system_prompt
        )

    async def run(self, collected_data: str) -> Setting:
        result = await self.agent.run(collected_data)
        return result.output
