import os

from dotenv import load_dotenv

from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult
from pydantic_ai.mcp import load_mcp_servers

from src.libs.utils.prompt_loader import load_system_prompt
from src.libs.utils.config_loader import load_mcp_config
from src.libs.agent_memory.context_memory import save_context, load_context
from src.agents.story_reviewer_agent.models import ValidationResult
from src.agents.story_creator_agent.models import Quest


load_dotenv()

class StoryReviewerAgent:
    AGENT_ID = "story_reviewer"

    def __init__(self, session_id: str):
        self.session_id = session_id

        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        servers = load_mcp_servers(load_mcp_config(__file__))

        self.messages = load_context(self.AGENT_ID, session_id)

        self.agent = Agent(
            llm_model,
            output_type=ValidationResult,
            system_prompt=system_prompt,
            toolsets=servers
        )

    def review_npc_locations(self, actors: list[str]) -> ValidationResult:
        prompt = f"""Review NPC location compatibility for dialogue scene.

NPCs in dialogue: {', '.join(actors)}

Check:
1. Can these NPCs physically be in the same location in World of Warcraft?
2. Use web_search to verify NPC locations from warcraft.wiki.gg
3. Determine if they can have a conversation together

Return validation result."""

        result = self.agent.run_sync(prompt, message_history=self.messages)
        self.messages = result.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
        return result.output

    def review_narration_perspective(self, text: str, player_name: str) -> ValidationResult:
        prompt = f"""Review narration for proper third-person perspective.

Player character name: {player_name}
Narration text: "{text}"

Check:
1. Must use third-person perspective (not "you/your")
2. Should use player name "{player_name}" when referring to player
3. "She/her" pronouns are acceptable for flow and immersion
4. Identify any second-person usage that needs correction

Return validation result."""

        result = self.agent.run_sync(prompt, message_history=self.messages)
        self.messages = result.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
        return result.output

    def review_quest_flow(self, quest: Quest) -> ValidationResult:
        prompt = f"""Review quest flow for World of Warcraft game mechanics.

Quest: {quest.title}

Quest structure:
- Introduction: {quest.sections.introduction.text[:100]}...
- Dialogue actors: {', '.join([line.actor for line in quest.sections.dialogue.lines])}
- Completion actors: {', '.join([line.actor for line in quest.sections.completion.lines])}

Check:
1. Does quest follow WoW mechanics (quest giver → objectives → turn-in)?
2. Are quest giver and turn-in NPCs appropriate?
3. Does quest flow make sense in WoW context?
4. Use web_search or knowledge base to verify quest structure

Return validation result."""

        result = self.agent.run_sync(prompt, message_history=self.messages)
        self.messages = result.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
        return result.output
