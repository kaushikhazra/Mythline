import os

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_system_prompt
from src.agents.chunker_agent.models.output_models import Chunk

load_dotenv()


class ChunkerAgent:
    AGENT_ID = "chunker"

    def __init__(self):
        llm_model = f"openrouter:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            output_type=list[Chunk],
            system_prompt=system_prompt
        )

    async def run(self, text: str, chunk_type: str, actor: str, reference: str) -> AgentRunResult[list[Chunk]]:
        prompt = f"""
text: {text}
chunk_type: {chunk_type}
actor: {actor}
reference: {reference}
"""
        agent_output = await self.agent.run(prompt)
        return agent_output
