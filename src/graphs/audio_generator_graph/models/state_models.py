from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import torch

from src.agents.shot_creator_agent.models.output_models import Shot


@dataclass
class AudioGeneratorSession:
    subject: str
    shots: list[Shot] = field(default_factory=list)
    actors: list[str] = field(default_factory=list)
    shot_index: int = 0
    current_shot: Optional[Shot] = None
    preprocessed_text: Optional[str] = None
    raw_audio: Optional[torch.Tensor] = None
    processed_audio: Optional[torch.Tensor] = None
