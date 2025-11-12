from typing import Optional
from pydantic import BaseModel


class Narration(BaseModel):
    text: str
    word_count: int


class DialogueLine(BaseModel):
    actor: str
    line: str


class DialogueLines(BaseModel):
    lines: list[DialogueLine]


class QuestSection(BaseModel):
    introduction: Optional[Narration] = None
    dialogue: Optional[DialogueLines] = None
    execution: Optional[Narration] = None
    completion: Optional[DialogueLines] = None


class Quest(BaseModel):
    title: str
    sections: QuestSection


class Story(BaseModel):
    title: str
    subject: str
    introduction: Optional[Narration] = None
    quests: list[Quest] = []
    conclusion: Optional[Narration] = None
