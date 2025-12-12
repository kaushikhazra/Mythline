from pydantic_graph import Graph

from src.graphs.story_research_graph.models.state_models import ResearchSession
from src.graphs.story_research_graph.models.research_models import ResearchBrief
from src.graphs.story_research_graph.nodes import (
    ParseInput,
    InitializeLoop,
    CheckHasMoreQuests,
    CrawlQuestPage,
    ExtractQuestData,
    CrawlNPCPages,
    EnrichNPCData,
    CrawlLocationPages,
    EnrichLocationData,
    StoreQuestResearch,
    IncrementIndex,
    ExtractSetting,
    SynthesizeBrief,
    SaveJSON
)


class StoryResearchGraph:

    def __init__(self, subject: str):
        self.subject = subject
        self.graph = Graph(
            nodes=[
                ParseInput,
                InitializeLoop,
                CheckHasMoreQuests,
                CrawlQuestPage,
                ExtractQuestData,
                CrawlNPCPages,
                EnrichNPCData,
                CrawlLocationPages,
                EnrichLocationData,
                StoreQuestResearch,
                IncrementIndex,
                ExtractSetting,
                SynthesizeBrief,
                SaveJSON
            ]
        )

    async def run(self) -> ResearchBrief | None:
        state = ResearchSession(subject=self.subject)
        result = await self.graph.run(ParseInput(), state=state)
        return state.research_brief
