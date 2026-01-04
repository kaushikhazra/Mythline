from pydantic import BaseModel


class Area(BaseModel):
    name: str
    x: float | None = None
    y: float | None = None


class Location(BaseModel):
    area: Area
    position: str
    visual: str
    landmarks: str


class NPC(BaseModel):
    name: str
    title: str
    personality: str
    lore: str
    location: Location


class ExecutionLocation(BaseModel):
    area: Area
    visual: str
    landmarks: str
    enemies: str


class Objectives(BaseModel):
    summary: str
    details: str


class QuestResearch(BaseModel):
    id: str
    title: str
    story_beat: str
    objectives: Objectives
    quest_giver: NPC
    turn_in_npc: NPC
    execution_location: ExecutionLocation
    story_text: str
    completion_text: str


class Setting(BaseModel):
    zone: str
    starting_location: str | None = None
    journey: str | None = None
    description: str
    lore_context: str


class ResearchBrief(BaseModel):
    chain_title: str
    setting: Setting
    quests: list[QuestResearch]


class QuestChainInput(BaseModel):
    chain_title: str
    quest_urls: list[str]
    quest_ids: dict[str, str] = {}
