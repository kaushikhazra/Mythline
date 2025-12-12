import os

from dotenv import load_dotenv

from pydantic_ai import Agent

from src.libs.utils.prompt_loader import load_system_prompt
from src.graphs.story_research_graph.models.research_models import QuestChainInput

load_dotenv()


class ResearchInputParserAgent:
    AGENT_ID = "research_input_parser"

    def __init__(self):
        llm_model = f"openrouter:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            output_type=QuestChainInput,
            system_prompt=system_prompt
        )

    async def run(self, content: str) -> QuestChainInput:
        result = await self.agent.run(content)
        return result.output
