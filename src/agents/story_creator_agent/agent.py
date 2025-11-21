from src.agents.story_creator_agent.models.story_models import Story
from src.graphs.story_creator_graph import StoryCreatorGraph


class StoryCreatorAgent:
    AGENT_ID = "story_creator"

    def __init__(self, session_id: str, player_name: str):
        self.session_id = session_id
        self.player_name = player_name

    async def run(self, subject: str, regenerate_plan: bool = False) -> Story | None:
        graph = StoryCreatorGraph(
            session_id=self.session_id,
            player_name=self.player_name
        )

        story = await graph.run(subject=subject, regenerate_plan=regenerate_plan)

        return story
