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
    introduction: Narration
    dialogue: DialogueLines
    execution: Narration
    completion: DialogueLines


class Quest(BaseModel):
    title: str
    sections: QuestSection


class Story(BaseModel):
    title: str
    subject: str
    introduction: Narration
    quests: list[Quest]
    conclusion: Narration
