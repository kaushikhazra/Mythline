import os

from dotenv import load_dotenv

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from src.libs.utils.prompt_loader import load_system_prompt

load_dotenv()


class NPCExtraction(BaseModel):
    name: str = Field(description="The NPC's full name exactly as shown (e.g., 'Ilthalaine', 'Melithar Staghelm').")
    title: str = Field(description="The NPC's title or role (e.g., 'Druid Trainer', 'Hunter Trainer'). Empty string if none.")
    personality: str = Field(description="Brief description of NPC's demeanor, attitude, and behavior based on dialogue and lore.")
    lore: str = Field(description="Background story, history, affiliations, and notable facts about the NPC.")
    location_area: str = Field(description="The zone or area name only (e.g., 'Shadowglen', 'Aldrassil'). Do not include coordinates or position details here.")
    location_x: float | None = Field(default=None, description="The X map coordinate as a number (e.g., 45.6). Extract from coordinates like [45.6, 74.6] or (45.6, 74.6).")
    location_y: float | None = Field(default=None, description="The Y map coordinate as a number (e.g., 74.6). Extract from coordinates like [45.6, 74.6] or (45.6, 74.6).")
    location_position: str = Field(description="Descriptive position details (e.g., 'near the training area', 'by the moonwell').")
    location_visual: str = Field(description="Visual description of the NPC's surroundings and environment.")
    location_landmarks: str = Field(description="Nearby notable landmarks, buildings, or features that help locate the NPC.")


class NPCExtractorAgent:
    AGENT_ID = "npc_extractor"

    def __init__(self):
        llm_model = f"openrouter:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            output_type=NPCExtraction,
            system_prompt=system_prompt
        )

    async def run(self, npc_page_content: str, location_hint: str = "") -> NPCExtraction:
        prompt = npc_page_content
        if location_hint:
            prompt += f"\n\nLocation hint from quest: {location_hint}"
        result = await self.agent.run(prompt)
        return result.output
