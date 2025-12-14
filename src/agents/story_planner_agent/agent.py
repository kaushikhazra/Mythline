import os
import json
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.mcp import load_mcp_servers
from src.libs.utils.prompt_loader import load_system_prompt
from src.libs.utils.config_loader import load_mcp_config
from src.agents.story_creator_agent.models.state_models import Todo

load_dotenv()


class StoryPlannerAgent:
    AGENT_ID = "story_planner"

    def __init__(self, session_id: str):
        self.session_id = session_id
        llm_model = f"openrouter:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        servers = load_mcp_servers(load_mcp_config(__file__))

        self.agent = Agent(
            llm_model,
            output_type=list[Todo],
            system_prompt=system_prompt,
            toolsets=servers
        )

    async def run(self, segment: dict, player_name: str) -> list[Todo]:
        segment_type = segment.get('segment_type', 'unknown')
        segment_json = json.dumps(segment, indent=2)

        prompt = f"""Player Character: {player_name}

Segment Type: {segment_type}

Segment Data:
{segment_json}

Generate todos for this {segment_type} segment based on the data above."""
        result = await self.agent.run(prompt)
        return result.output
