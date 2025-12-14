import os

from dotenv import load_dotenv

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from src.libs.utils.prompt_loader import load_system_prompt

load_dotenv()


class QuestExtraction(BaseModel):
    title: str
    story_beat: str
    objectives_summary: str
    objectives_details: str
    quest_giver_name: str
    quest_giver_location_hint: str = Field(description="Zone or area name where quest giver is located (e.g., 'Shadowglen', 'Aldrassil'). Do not include coordinates here.")
    quest_giver_location_x: float | None = Field(default=None, description="X map coordinate as a number (e.g., 45.6). Extract from coordinates like [45.6, 74.6] or (45.6, 74.6).")
    quest_giver_location_y: float | None = Field(default=None, description="Y map coordinate as a number (e.g., 74.6). Extract from coordinates like [45.6, 74.6] or (45.6, 74.6).")
    turn_in_npc_name: str
    turn_in_npc_location_hint: str = Field(description="Zone or area name where turn-in NPC is located. Do not include coordinates here.")
    turn_in_npc_location_x: float | None = Field(default=None, description="X map coordinate as a number for turn-in NPC location.")
    turn_in_npc_location_y: float | None = Field(default=None, description="Y map coordinate as a number for turn-in NPC location.")
    zone: str
    execution_area: str
    enemies: str
    story_text: str
    completion_text: str


class QuestExtractorAgent:
    AGENT_ID = "quest_extractor"

    def __init__(self):
        llm_model = f"openrouter:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            output_type=QuestExtraction,
            system_prompt=system_prompt
        )

    async def run(self, quest_page_content: str) -> QuestExtraction:
        result = await self.agent.run(quest_page_content)
        return result.output
