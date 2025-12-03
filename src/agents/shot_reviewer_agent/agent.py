import os

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_system_prompt
from src.agents.shot_reviewer_agent.models.output_models import ShotReviewResult
from src.agents.shot_creator_agent.models.output_models import Shot

load_dotenv()


class ShotReviewerAgent:
    AGENT_ID = "shot_reviewer"

    def __init__(self):
        llm_model = f"openrouter:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            output_type=ShotReviewResult,
            system_prompt=system_prompt
        )

    async def run(
        self,
        shot: Shot,
        chunk_text: str,
        chunk_actor: str,
        chunk_type: str,
        chunk_reference: str
    ) -> AgentRunResult[ShotReviewResult]:
        prompt = f"""
## Generated Shot

shot_number: {shot.shot_number}
actor: {shot.actor}
temperature: {shot.temperature}
exaggeration: {shot.exaggeration}
cfg_weight: {shot.cfg_weight}
language: {shot.language}
text: {shot.text}
reference: {shot.reference}
camera_zoom: {shot.camera_zoom.value}
camera_angle: {shot.camera_angle.value}
player_actions: {shot.player_actions}
backdrop: {shot.backdrop}
duration_seconds: {shot.duration_seconds}

## Original Chunk Context

chunk_text: {chunk_text}
chunk_actor: {chunk_actor}
chunk_type: {chunk_type}
chunk_reference: {chunk_reference}

Please review this shot against the parameter rules and quality standards.
"""
        agent_output = await self.agent.run(prompt)
        return agent_output
