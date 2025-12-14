import os

from dotenv import load_dotenv

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from src.libs.utils.prompt_loader import load_system_prompt

load_dotenv()


class LocationExtraction(BaseModel):
    area: str = Field(description="The zone or area name only (e.g., 'Shadowglen', 'Northshire Valley'). Do not include coordinates here.")
    area_x: float | None = Field(default=None, description="The X map coordinate as a number if available.")
    area_y: float | None = Field(default=None, description="The Y map coordinate as a number if available.")
    visual: str = Field(description="Visual description of the location's environment, atmosphere, lighting, and terrain.")
    landmarks: str = Field(description="Notable landmarks, structures, or geographic features in the area.")
    enemies: str = Field(description="Hostile creatures, NPCs, or factions found in this location.")


class LocationExtractorAgent:
    AGENT_ID = "location_extractor"

    def __init__(self):
        llm_model = f"openrouter:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            output_type=LocationExtraction,
            system_prompt=system_prompt
        )

    async def run(self, location_page_content: str) -> LocationExtraction:
        result = await self.agent.run(location_page_content)
        return result.output
