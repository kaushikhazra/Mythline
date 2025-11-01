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


class Narration(BaseModel):
    text: str
    word_count: int

    @model_validator(mode='after')
    def validate_third_person_perspective(self):
        if _reviewer_agent is None or _player_name is None:
            return self

        try:
            print(colored("[*] Validating third-person perspective in narration", "grey"))

            result = _reviewer_agent.review_narration_perspective(self.text, _player_name)

            if not result.valid:
                print(colored(f"[!] Validation failed: {result.error}", "red"))
                raise ValueError(f"{result.error}\nSuggestion: {result.suggestion}")

            print(colored("[+] Third-person perspective validation passed", "green"))
        except Exception as e:
            print(colored(f"[!] Validation error (skipping): {str(e)[:100]}", "yellow"))

        return self


class DialogueLine(BaseModel):
    actor: str
    line: str


class DialogueLines(BaseModel):
    lines: list[DialogueLine]

    @model_validator(mode='after')
    def validate_npc_location_conflict(self):
        if _reviewer_agent is None:
            return self

        actors = [line.actor for line in self.lines]

        if len(actors) <= 1:
            return self

        try:
            print(colored(f"[*] Validating NPC location compatibility for: {', '.join(actors)}", "grey"))

            result = _reviewer_agent.review_npc_locations(actors)

            if not result.valid:
                print(colored(f"[!] Validation failed: {result.error}", "red"))
                raise ValueError(f"{result.error}\nSuggestion: {result.suggestion}")

            print(colored("[+] NPC location validation passed", "green"))
        except Exception as e:
            print(colored(f"[!] Validation error (skipping): {str(e)[:100]}", "yellow"))

        return self


class QuestSection(BaseModel):
    introduction: Narration
    dialogue: DialogueLines
    execution: Narration
    completion: DialogueLines


class Quest(BaseModel):
    title: str
    sections: QuestSection

    @model_validator(mode='after')
    def validate_quest_flow_mechanics(self):
        if _reviewer_agent is None or _subject is None:
            return self

        try:
            print(colored(f"[*] Validating quest flow mechanics for: {self.title}", "grey"))

            result = _reviewer_agent.review_quest_flow(self)

            if not result.valid:
                print(colored(f"[!] Validation failed: {result.error}", "red"))
                raise ValueError(f"{result.error}\nSuggestion: {result.suggestion}")

            print(colored("[+] Quest flow mechanics validation passed", "green"))
        except Exception as e:
            print(colored(f"[!] Validation error (skipping): {str(e)[:100]}", "yellow"))

        return self


class Story(BaseModel):
    title: str
    subject: str
    introduction: Narration
    quests: list[Quest]
    conclusion: Narration
