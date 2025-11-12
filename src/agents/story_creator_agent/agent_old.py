import os
import json
from datetime import datetime

from dotenv import load_dotenv
from termcolor import colored

from pydantic_ai.mcp import load_mcp_servers
from pydantic_ai.run import AgentRunResult
from pydantic_ai import Agent, RunContext

from src.agents.user_preference_agent import UserPreferenceAgent
from src.agents.story_creator_agent.models import Story, Narration, DialogueLine, DialogueLines, Quest, QuestSection
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.story_planner_agent import StoryPlannerAgent

from src.libs.agent_memory.context_memory import save_context, load_context, summarize_context
from src.libs.agent_memory.long_term_memory import save_long_term_memory, load_long_term_memory
from src.libs.filesystem.file_operations import read_file, write_file
from src.libs.filesystem.directory_operations import create_directory
from src.libs.utils.prompt_loader import load_system_prompt
from src.libs.utils.config_loader import load_mcp_config


load_dotenv()

class StoryCreatorAgent:
    AGENT_ID = "story_creator"


    def __init__(self, session_id: str, player_name: str):
        self.session_id = session_id
        self.player_name = player_name

        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)
        system_prompt += self._load_preferences()
        system_prompt += f"\n\n## Player Character:\nThe player character's name is: {player_name}\nAlways use third-person perspective with the player's name in narration."

        self.servers = load_mcp_servers(load_mcp_config(__file__))

        self.messages = load_context(self.AGENT_ID, session_id)

        self._reviewer_agent = ReviewerAgent(session_id=session_id)
        self._planner_agent = StoryPlannerAgent()

        self.agent = Agent(
            llm_model,
            output_type=Story,
            system_prompt=system_prompt,
            toolsets=self.servers,
            history_processors=[summarize_context]
        )

        self._user_preference_agent = UserPreferenceAgent()

        @self.agent.tool
        async def save_user_preference(ctx: RunContext, user_message: str):
            print(colored(f"[*] Identifying user's preference", "grey"))

            response = await self._user_preference_agent.run(f"Extract story preferences from this message:\n{user_message}")

            print(colored(f"\n[*] Got response:\n{response.output}", "grey"))

            if response.output.lower().strip() != "none":
                save_long_term_memory(self.AGENT_ID, response.output)
                print(colored(f"[+] Preference saved to long-term memory", "green"))

            return response.output

    def _load_preferences(self) -> str:
        preferences = load_long_term_memory(self.AGENT_ID)
        if not preferences:
            return ""

        preferences_text = "\n\n## Memory:\n"

        for pref in preferences:
            preferences_text += f"- {pref['preference']}\n"

        return preferences_text

    def _save_story_json(self, story: Story, subject: str):
        dir_path = f"output/{subject}"
        file_path = f"{dir_path}/story.json"

        create_directory(dir_path)

        story_json = story.model_dump_json(indent=2)
        result = write_file(file_path, story_json)

        if result.startswith("Successfully"):
            print(colored(f"[+] Story saved to {file_path}", "green"))
        else:
            print(colored(f"[!] Error saving story: {result}", "red"))

    async def _execute_todo(self, todo, story: Story, research_content: str):
        from src.agents.story_planner_agent.models import StoryTodo

        max_retries = 3

        for attempt in range(1, max_retries + 1):
            self.messages = []

            piece = await self._generate_piece(todo, story, research_content)

            validation = await self._validate_piece(piece, todo)

            if validation.valid:
                print(colored(f"[+] Piece validated successfully", "green"))
                return piece

            print(colored(f"[!] Validation failed (attempt {attempt}/{max_retries}): {validation.error}", "yellow"))

            if attempt < max_retries:
                print(colored(f"[*] Retrying...", "cyan"))
                continue

        raise ValueError(f"Failed to generate {todo.type} after {max_retries} attempts")

    async def _generate_piece(self, todo, story: Story, research_content: str):
        from src.agents.story_planner_agent.models import StoryTodo

        prompt = self._build_todo_prompt(todo, story, research_content)

        output_type = self._get_output_type_for_todo(todo)

        temp_agent = Agent(
            f"openai:{os.getenv('LLM_MODEL')}",
            output_type=output_type,
            system_prompt=load_system_prompt(__file__) + self._load_preferences() + f"\n\n## Player Character:\nThe player character's name is: {self.player_name}\nAlways use third-person perspective with the player's name in narration.",
            toolsets=self.servers,
            history_processors=[summarize_context]
        )

        result = await temp_agent.run(prompt)

        return result.output

    def _get_output_type_for_todo(self, todo):
        from src.agents.story_planner_agent.models import StoryTodo

        if todo.type == "introduction":
            return Narration
        elif todo.type == "quest_introduction":
            return Narration
        elif todo.type == "quest_dialogue":
            return DialogueLines
        elif todo.type == "quest_execution":
            return Narration
        elif todo.type == "quest_completion":
            return DialogueLines
        elif todo.type == "conclusion":
            return Narration
        else:
            raise ValueError(f"Unknown todo type: {todo.type}")

    def _build_todo_prompt(self, todo, story: Story, research_content: str) -> str:
        from src.agents.story_planner_agent.models import StoryTodo

        base_context = f"""Research content:
        {research_content}

        Subject: {story.subject}
        Player name: {self.player_name}

        """

        if todo.type == "introduction":
            return base_context + f"""Generate the story introduction narration.

            Description: {todo.description}

            Requirements:
            - Use third-person perspective with player name "{self.player_name}"
            - Create an immersive opening
            - Set the scene for the story
            - Target word count: 100-200 words"""

        elif todo.type == "quest_introduction":
            return base_context + f"""Generate the introduction narration for quest: {todo.quest_title}

            Description: {todo.description}

            Requirements:
            - Use third-person perspective with player name "{self.player_name}"
            - Describe the quest context and objectives
            - Target word count: 100-150 words"""

        elif todo.type == "quest_dialogue":
            return base_context + f"""Generate the quest acceptance dialogue for: {todo.quest_title}

            Description: {todo.description}

            Requirements:
            - Create dialogue between quest giver NPC and player
            - Follow WoW quest patterns
            - Include quest giver name as actor
            - 2-4 dialogue lines"""

        elif todo.type == "quest_execution":
            return base_context + f"""Generate the quest execution narration for: {todo.quest_title}

            Description: {todo.description}

            Requirements:
            - Use third-person perspective with player name "{self.player_name}"
            - Describe player completing quest objectives
            - Target word count: 150-250 words"""

        elif todo.type == "quest_completion":
            return base_context + f"""Generate the quest turn-in dialogue for: {todo.quest_title}

            Description: {todo.description}

            Requirements:
            - Create dialogue for quest completion
            - Include turn-in NPC as actor
            - 2-3 dialogue lines
            - Convey quest resolution"""

        elif todo.type == "conclusion":
            return base_context + f"""Generate the story conclusion narration.

            Description: {todo.description}

            Requirements:
            - Use third-person perspective with player name "{self.player_name}"
            - Wrap up the story arc
            - Reflect on quests completed
            - Target word count: 100-200 words"""

        else:
            raise ValueError(f"Unknown todo type: {todo.type}")

    async def _validate_piece(self, piece, todo):
        from src.agents.story_planner_agent.models import StoryTodo
        from src.agents.reviewer_agent.models import ValidationResult

        self._reviewer_agent.messages = []

        prompt = self._build_validation_prompt(piece, todo)

        result = await self._reviewer_agent.run(prompt)
        return result

    def _build_validation_prompt(self, piece, todo) -> str:
        from src.agents.story_planner_agent.models import StoryTodo

        if todo.type in ["introduction", "quest_introduction", "quest_execution", "conclusion"]:
            return f"""Review narration for proper third-person perspective.

            Player character name: {self.player_name}
            Narration text: "{piece.text}"

            Check:
            1. Must use third-person perspective (not "you/your")
            2. Should use player name "{self.player_name}" when referring to player
            3. "She/her/he/him" pronouns are acceptable for flow and immersion
            4. Identify any second-person usage that needs correction"""

        elif todo.type in ["quest_dialogue", "quest_completion"]:
            actors = [line.actor for line in piece.lines]

            if len(actors) > 1:
                return f"""Review NPC location compatibility for dialogue scene.

                NPCs in dialogue: {', '.join(actors)}

                Check:
                1. Can these NPCs physically be in the same location in World of Warcraft?
                2. Use web_search to verify NPC locations from warcraft.wiki.gg
                3. Determine if they can have a conversation together"""
            else:
                return f"""Review dialogue for WoW quest pattern.

                Quest NPC: {actors[0] if actors else 'unknown'}
                Dialogue: {[line.line for line in piece.lines]}

                Check:
                1. Does dialogue fit WoW quest style?
                2. Is NPC appropriate for this quest type?
                3. Are dialogue lines clear and engaging?"""

        else:
            raise ValueError(f"Unknown todo type: {todo.type}")

    def _add_piece_to_story(self, story: Story, piece, todo) -> Story:
        from src.agents.story_planner_agent.models import StoryTodo

        if todo.type == "introduction":
            story.introduction = piece

        elif todo.type == "conclusion":
            story.conclusion = piece

        elif todo.type == "quest_introduction":
            quest = Quest(title=todo.quest_title, sections=QuestSection())
            quest.sections.introduction = piece
            story.quests.append(quest)

        elif todo.type == "quest_dialogue":
            for quest in story.quests:
                if quest.title == todo.quest_title:
                    quest.sections.dialogue = piece
                    break

        elif todo.type == "quest_execution":
            for quest in story.quests:
                if quest.title == todo.quest_title:
                    quest.sections.execution = piece
                    break

        elif todo.type == "quest_completion":
            for quest in story.quests:
                if quest.title == todo.quest_title:
                    quest.sections.completion = piece
                    break

        if not story.title:
            story.title = f"The {story.subject.title()} Chronicles"

        return story

    async def run(self, subject: str) -> Story:
        print(colored("\n[*] Reading research notes...", "cyan"))
        research_content = read_file(f"output/{subject}/research.md")

        if research_content.startswith("Error:"):
            raise ValueError(f"Research file not found for subject: {subject}")

        print(colored(f"[+] Research loaded", "green"))

        print(colored("\n[*] Generating story plan...", "cyan"))
        plan = await self._planner_agent.run(research_content)
        print(colored(f"[+] Plan created with {len(plan.todos)} todos", "green"))

        story = Story(title="", subject=subject)

        for i, todo in enumerate(plan.todos, 1):
            print(colored(f"\n[*] Processing todo {i}/{len(plan.todos)}: {todo.type}", "cyan"))

            piece = await self._execute_todo(todo, story, research_content)
            story = self._add_piece_to_story(story, piece, todo)
            self._save_story_json(story, subject)

        print(colored("\n[+] Story generation complete!", "green"))
        return story
