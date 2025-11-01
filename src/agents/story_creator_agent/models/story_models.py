from abc import ABC, abstractmethod
from pydantic import BaseModel, model_validator
from termcolor import colored


_reviewer_agent = None
_player_name = None
_subject = None


def init_validators(reviewer_agent, player_name: str, subject: str):
    global _reviewer_agent, _player_name, _subject
    _reviewer_agent = reviewer_agent
    _player_name = player_name
    _subject = subject


class ReviewEnabled(BaseModel, ABC):
    @abstractmethod
    def review(self) -> str:
        pass

    @model_validator(mode='after')
    def validate_content(self):
        if _reviewer_agent is None:
            return self

        try:
            prompt = self.review()
            print(colored(f"[*] Validating: {self.__class__.__name__}", "grey"))

            result = _reviewer_agent.run(prompt)

            if not result.valid:
                print(colored(f"[!] Validation failed: {result.error}", "red"))
                raise ValueError(f"{result.error}\nSuggestion: {result.suggestion}")

            print(colored(f"[+] Validation passed: {self.__class__.__name__}", "green"))
        except Exception as e:
            print(colored(f"[!] Validation error (skipping): {str(e)[:100]}", "yellow"))

        return self


class Narration(ReviewEnabled):
    text: str
    word_count: int

    def review(self) -> str:
        return f"""Review narration for proper third-person perspective.

Player character name: {_player_name}
Narration text: "{self.text}"

Check:
1. Must use third-person perspective (not "you/your")
2. Should use player name "{_player_name}" when referring to player
3. "She/her/he/him" pronouns are acceptable for flow and immersion
4. Identify any second-person usage that needs correction

Return validation result."""


class DialogueLine(BaseModel):
    actor: str
    line: str


class DialogueLines(ReviewEnabled):
    lines: list[DialogueLine]

    def review(self) -> str:
        actors = [line.actor for line in self.lines]

        if len(actors) <= 1:
            return f"""Single actor dialogue - no location validation needed.
Actor: {actors[0] if actors else 'none'}

Return valid result."""

        return f"""Review NPC location compatibility for dialogue scene.

NPCs in dialogue: {', '.join(actors)}

Check:
1. Can these NPCs physically be in the same location in World of Warcraft?
2. Use web_search to verify NPC locations from warcraft.wiki.gg
3. Determine if they can have a conversation together
4. Consider the recording/cinematic constraints (impossible scenes can't be recorded)

Return validation result."""


class QuestSection(BaseModel):
    introduction: Narration
    dialogue: DialogueLines
    execution: Narration
    completion: DialogueLines


class Quest(ReviewEnabled):
    title: str
    sections: QuestSection

    def review(self) -> str:
        dialogue_actors = ', '.join([line.actor for line in self.sections.dialogue.lines])
        completion_actors = ', '.join([line.actor for line in self.sections.completion.lines])

        return f"""Review quest flow for World of Warcraft game mechanics.

Quest: {self.title}
Subject: {_subject}

Quest structure:
- Introduction: {self.sections.introduction.text[:100]}...
- Dialogue actors: {dialogue_actors}
- Completion actors: {completion_actors}

Check:
1. Does quest follow WoW mechanics (quest giver → objectives → turn-in)?
2. Are quest giver and turn-in NPCs appropriate?
3. Does quest flow make sense in WoW context?
4. Use web_search or knowledge base to verify quest structure for {_subject}

Return validation result."""


class Story(BaseModel):
    title: str
    subject: str
    introduction: Narration
    quests: list[Quest]
    conclusion: Narration
