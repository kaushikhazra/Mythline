import os

from dotenv import load_dotenv

from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_system_prompt
from src.agents.quality_assessor.models.output_models import QualityAssessment

load_dotenv()

class QualityAssessorAgent:
    AGENT_ID = "quality_assessor"

    def __init__(self):
        llm_model = f"openrouter:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            output_type=QualityAssessment,
            system_prompt=system_prompt
        )

    async def run(self, prompt: str) -> AgentRunResult[QualityAssessment]:
        agent_output = await self.agent.run(prompt)
        return agent_output
