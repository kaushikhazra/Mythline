import os

from dotenv import load_dotenv
from termcolor import colored

from pydantic_ai.mcp import load_mcp_servers
from pydantic_ai.run import AgentRunResult
from pydantic_ai import (
    Agent, 
    RunContext, 
    ModelMessage, 
    ToolCallPart,
    AgentStreamEvent,
    PartStartEvent,
    PartDeltaEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    TextPartDelta,
    ThinkingPartDelta,
    ToolCallPartDelta,
)

from src.libs.utils.prompt_loader import load_system_prompt, load_prompt
from src.libs.utils.config_loader import load_mcp_config
from src.libs.agent_memory.context_memory import save_context, load_context, summarize_context
from src.libs.agent_memory.long_term_memory import save_long_term_memory, load_long_term_memory
from src.agents.narrator_agent import NarratorAgent
from src.agents.dialog_creator_agent import DialogCreatorAgent
from src.agents.user_preference_agent import UserPreferenceAgent



load_dotenv()

class StoryResearcher:
    AGENT_ID = "story_researcher"

    
    def __init__(self, session_id: str):
        self.session_id = session_id

        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)
        system_prompt += self._load_preferences()

        # print(f"System Prompt:\n{system_prompt}\n")

        servers = load_mcp_servers(load_mcp_config(__file__))

        self.messages = load_context(self.AGENT_ID, session_id)

        self.agent = Agent(
            llm_model,
            system_prompt=system_prompt,
            toolsets=servers,
            history_processors=[summarize_context]
        )

        self._narrator_agent = NarratorAgent(session_id)
        self._dialog_agent = DialogCreatorAgent(session_id)
        self._user_preference_agent = UserPreferenceAgent()

        @self.agent.tool
        async def create_dialog(ctx: RunContext, reference_text: str, actors: list[str]) -> str:
            print(colored(f"""⚙ Calling Dialog Creator with 
                          \nActors: {actors} 
                          \nReference: {reference_text}""","grey"))

            prompt_template = load_prompt(__file__, "create_dialog")
            prompt = prompt_template.format(actors=actors, reference_text=reference_text)
            response = await self._dialog_agent.run(prompt)

            print(colored(f"""\n⚙ Got response:\n{response.output}""", "grey"))

            return response.output
        
        @self.agent.tool
        async def create_narration(ctx: RunContext, reference_text: str, word_count: int) -> str:
            print(colored(f"""⚙ Calling Narrator with 
                          \nWord Count: {word_count} 
                          \nReference: {reference_text}""","grey"))

            prompt_template = load_prompt(__file__, "create_narration")
            prompt = prompt_template.format(word_count=word_count, reference_text=reference_text)
            response = await self._narrator_agent.run(prompt)

            print(colored(f"""\n⚙ Got response:
                          \n{response.output}""", "grey"))

            return response.output
        
        @self.agent.tool
        async def save_user_preference(ctx: RunContext, user_message: str):
            print(f"""⚙ Identifying user's preference""")

            prompt_template = load_prompt(__file__, "save_user_preference")
            prompt = prompt_template.format(user_message=user_message)
            response = await self._user_preference_agent.run(prompt)

            print(f"""\n⚙ Got response:\n{response.output}""")

            if response.output.lower().strip() != "none":
                save_long_term_memory(self.AGENT_ID, response.output)
                print(f"""✓ Preference saved to long-term memory""")

            return response.output

    def _load_preferences(self) -> str:
        preferences = load_long_term_memory(self.AGENT_ID)
        if not preferences:
            return ""

        preferences_text = "\n\n##Memory:\n"

        for pref in preferences:
            preferences_text += f"- {pref['preference']}\n"

        return preferences_text
    
    def run(self, prompt: str) -> AgentRunResult:
        agent_output = self.agent.run_sync(prompt, message_history=self.messages)
        self.messages = agent_output.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
        return agent_output
    
