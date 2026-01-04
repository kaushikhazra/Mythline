from dataclasses import dataclass, field
from typing import Optional

from src.graphs.story_research_graph.models.research_models import (
    QuestResearch,
    Setting,
    ResearchBrief
)


@dataclass
class ResearchSession:
    subject: str

    chain_title: str = ""
    quest_urls: list[str] = field(default_factory=list)
    quest_ids: dict[str, str] = field(default_factory=dict)
    parsed_setting: dict = field(default_factory=dict)
    parsed_roleplay: dict[str, str] = field(default_factory=dict)
    parsed_quest_chain: dict = field(default_factory=dict)

    quest_contents: dict[str, str] = field(default_factory=dict)
    npc_contents: dict[str, str] = field(default_factory=dict)
    location_contents: dict[str, str] = field(default_factory=dict)

    current_quest_content: str = ""
    current_npc_urls: list[str] = field(default_factory=list)
    current_location_urls: list[str] = field(default_factory=list)

    quest_data: list[QuestResearch] = field(default_factory=list)

    quest_index: int = 0

    setting: Optional[Setting] = None
    research_brief: Optional[ResearchBrief] = None
