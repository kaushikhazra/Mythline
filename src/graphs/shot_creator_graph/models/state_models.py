from dataclasses import dataclass, field
from typing import Optional

from src.agents.story_creator_agent.models.story_models import Story, Quest
from src.agents.chunker_agent.models.output_models import Chunk
from src.agents.shot_creator_agent.models.output_models import Shot


@dataclass
class ShotCreatorSession:
    subject: str
    story: Optional[Story] = None
    chunks: list[Chunk] = field(default_factory=list)
    quest_index: int = 0
    current_quest: Optional[Quest] = None
    current_index: int = 0
    shots: list[Shot] = field(default_factory=list)
    missing_indices: list[int] = field(default_factory=list)
    processing_missing: bool = False
