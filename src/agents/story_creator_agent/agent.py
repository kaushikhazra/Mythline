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
from src.agents.story_creator_agent.models import Story


load_dotenv()

class StoryCreatorAgent:
    AGENT_ID = "story_creator"


    def __init__(self, session_id: str):
        self.session_id = session_id

        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)
        system_prompt += self._load_preferences()

        self.servers = load_mcp_servers(load_mcp_config(__file__))

        self.messages = load_context(self.AGENT_ID, session_id)

        self.agent = Agent(
            llm_model,
            output_type=Story,
            system_prompt=system_prompt,
            toolsets=self.servers,
            history_processors=[summarize_context]
        )

        self._user_preference_agent = UserPreferenceAgent()

        @self.agent.tool
        async def read_research_notes(ctx: RunContext, subject: str) -> str:
            print(colored(f"⚙ Reading research notes for: {subject}", "grey"))

            path = f"output/{subject}/research.md"

            try:
                result = await self.servers["filesystem"].call_tool("read", {"path": path})
                print(colored(f"✓ Research notes loaded from {path}", "green"))
                return result
            except Exception as e:
                error_msg = f"No research notes found at {path}. Error: {str(e)}\nYou may need to perform web research to fill in the gaps."
                print(colored(error_msg, "yellow"))
                return error_msg

        @self.agent.tool
        async def save_story_json(ctx: RunContext, subject: str, story: Story) -> str:
            print(colored(f"⚙ Saving story for: {subject}", "grey"))

            dir_path = f"output/{subject}"
            file_path = f"{dir_path}/story.json"

            try:
                await self.servers["filesystem"].call_tool("create_dir", {"path": dir_path})
            except:
                pass

            story_json = story.model_dump_json(indent=2)

            try:
                await self.servers["filesystem"].call_tool("write", {"path": file_path, "content": story_json})
                success_msg = f"Story saved successfully to {file_path}"
                print(colored(success_msg, "green"))
                return success_msg
            except Exception as e:
                error_msg = f"Failed to save story: {str(e)}"
                print(colored(error_msg, "red"))
                return error_msg

        @self.agent.tool
        async def save_user_preference(ctx: RunContext, user_message: str):
            print(colored(f"⚙ Identifying user's preference", "grey"))

            response = await self._user_preference_agent.run(f"Extract story preferences from this message:\n{user_message}")

            print(colored(f"\n⚙ Got response:\n{response.output}", "grey"))

            if response.output.lower().strip() != "none":
                save_long_term_memory(self.AGENT_ID, response.output)
                print(colored(f"✓ Preference saved to long-term memory", "green"))

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
