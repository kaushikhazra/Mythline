import os

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_system_prompt
from src.agents.story_reviewer_agent.models.output_models import StoryReviewResult

load_dotenv()


class StoryReviewerAgent:
    AGENT_ID = "story_reviewer"

    def __init__(self):
        llm_model = f"openrouter:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            output_type=StoryReviewResult,
            system_prompt=system_prompt
        )

    async def run(
        self,
        content: str,
        content_type: str,
        research_context: str,
        segment_prompt: str,
        player_name: str
    ) -> AgentRunResult[StoryReviewResult]:
        prompt = f"""
## Generated Content ({content_type})

{content}

## Research Context

{research_context}

## Segment Prompt (What Was Requested)

{segment_prompt}

## Player Character Name

{player_name}

Please review this content against the research and quality standards.
"""
        agent_output = await self.agent.run(prompt)
        return agent_output
