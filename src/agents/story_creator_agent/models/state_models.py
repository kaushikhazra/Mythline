from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel
from src.agents.story_creator_agent.models.story_models import Narration, DialogueLines


class StorySegment(BaseModel):
    type: Literal['introduction', 'quest', 'conclusion']
    sub_type: Optional[Literal['quest_introduction', 'quest_dialogue', 'quest_execution', 'quest_conclusion']] = None
    quest_name: Optional[str] = None
    description: str = ""
    prompt: str = ""
    output: Optional[Narration | DialogueLines] = None


class Todo(BaseModel):
    item: StorySegment
    status: Literal['pending', 'in_progress', 'done'] = 'pending'


class StorySession(BaseModel):
    todo_list: list[Todo]
    subject: str
    player: str
    session_id: str
    current_todo_index: int = 0
