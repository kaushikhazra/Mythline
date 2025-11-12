from pydantic_graph import Graph

from src.agents.story_creator_agent.models.state_models import StorySession
from src.graphs.story_creator_graph.nodes import (
    GetStoryResearch,
    CreateTODO,
    GetNextTODO,
    CreateStorySegment,
    ReviewOutput,
    WriteToFile
)


class StoryCreatorGraph:

    def __init__(self, session_id: str, player_name: str):
        self.session_id = session_id
        self.player_name = player_name

        self.graph = Graph(
            nodes=[
                GetStoryResearch,
                CreateTODO,
                GetNextTODO,
                CreateStorySegment,
                ReviewOutput,
                WriteToFile
            ]
        )

    async def run(self, subject: str) -> None:
        state = StorySession(
            todo_list=[],
            subject=subject,
            player=self.player_name,
            session_id=self.session_id
        )

        await self.graph.run(GetStoryResearch(), state=state)
