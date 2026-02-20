from typing import Literal, Optional
from pydantic import BaseModel


class Narration(BaseModel):
    text: str
    word_count: int


class DialogueLine(BaseModel):
    actor: str
    line: str


class DialogueLines(BaseModel):
    lines: list[DialogueLine]


class StorySegment(BaseModel):
    quest_ids: list[str]
    phase: Literal["accept", "exec", "complete"]
    section: Literal["intro", "dialogue", "narration"]
    text: Optional[str] = None
    lines: Optional[list[DialogueLine]] = None
    word_count: Optional[int] = None


class Story(BaseModel):
    title: str
    subject: str
    introduction: Optional[Narration] = None
    segments: list[StorySegment] = []
    conclusion: Optional[Narration] = None


class QuestSection(BaseModel):
    introduction: Optional[Narration] = None
    dialogue: Optional[DialogueLines] = None
    execution: Optional[Narration] = None
    completion: Optional[DialogueLines] = None


class Quest(BaseModel):
    id: str
    title: str
    sections: QuestSection
