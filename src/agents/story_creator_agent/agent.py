import os
import json
from datetime import datetime

from dotenv import load_dotenv
from termcolor import colored

from pydantic_ai.mcp import load_mcp_servers
from pydantic_ai.run import AgentRunResult
from pydantic_ai import Agent, RunContext

from src.libs.utils.prompt_loader import load_system_prompt
from src.libs.utils.config_loader import load_mcp_config
from src.libs.agent_memory.context_memory import save_context, load_context, summarize_context
from src.libs.agent_memory.long_term_memory import save_long_term_memory, load_long_term_memory
from src.agents.user_preference_agent import UserPreferenceAgent
from src.agents.story_creator_agent.models import Story, init_validators
from src.agents.story_reviewer_agent import StoryReviewerAgent
from src.libs.filesystem.file_operations import read_file, write_file
from src.libs.filesystem.directory_operations import create_directory


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

        try:
            self._reviewer_agent = StoryReviewerAgent(session_id=session_id)
            init_validators(self._reviewer_agent, player_name, session_id)
            print(colored("[+] Story validation enabled", "green"))
        except Exception as e:
            print(colored(f"[!] Could not initialize reviewer agent: {str(e)}", "yellow"))
            print(colored("[!] Story validation disabled - MCP servers may not be running", "yellow"))
            init_validators(None, player_name, session_id)

        self.agent = Agent(
            llm_model,
            output_type=Story,
            system_prompt=system_prompt,
            toolsets=self.servers,
            history_processors=[summarize_context]
        )

        self._user_preference_agent = UserPreferenceAgent()

        @self.agent.tool
        def read_research_notes(ctx: RunContext, subject: str) -> str:
            print(colored(f"[*] Reading research notes for: {subject}", "grey"))

            path = f"output/{subject}/research.md"
            result = read_file(path)

            if result.startswith("Error:"):
                error_msg = f"{result}\nYou may need to perform web research to fill in the gaps."
                print(colored(error_msg, "yellow"))
                return error_msg
            else:
                print(colored(f"[+] Research notes loaded from {path}", "green"))
                return result

        @self.agent.tool
        def save_story_json(ctx: RunContext, subject: str, story: Story) -> str:
            print(colored(f"[*] Saving story for: {subject}", "grey"))

            dir_path = f"output/{subject}"
            file_path = f"{dir_path}/story.json"

            create_directory(dir_path)

            story_json = story.model_dump_json(indent=2)
            result = write_file(file_path, story_json)

            if result.startswith("Successfully"):
                print(colored(result, "green"))
                return result
            else:
                print(colored(result, "red"))
                return result

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

    def run(self, prompt: str) -> AgentRunResult[Story]:
        agent_output = self.agent.run_sync(prompt, message_history=self.messages)
        self.messages = agent_output.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
        return agent_output
