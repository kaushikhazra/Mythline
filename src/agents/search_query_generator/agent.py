import os
from dotenv import load_dotenv
from pydantic_ai import Agent

from src.agents.search_query_generator.models.output_models import SearchQueries
from src.libs.utils.prompt_loader import load_system_prompt

load_dotenv()

class SearchQueryGeneratorAgent:

    AGENT_ID = "search_query_generator"

    def __init__(self):
        llm_model = f"openrouter:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            output_type=SearchQueries,
            system_prompt=system_prompt
        )

    async def run(self, content: str) -> SearchQueries:
        result = await self.agent.run(content)
        return result.output
