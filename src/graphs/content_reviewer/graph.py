from pydantic_graph import Graph

from src.graphs.content_reviewer.models.state_models import ReviewState
from src.graphs.content_reviewer.models.output_models import ReviewResult
from src.graphs.content_reviewer.nodes import (
    LoadOrCreateSession,
    GenerateSearchQueries,
    GetSavedContext,
    CollectWebData,
    PerformAIReview,
    UpdateSession,
    CheckCompletion,
    WipeSession,
    SaveSession,
    PopulateResult
)

class ContentReviewGraph:

    def __init__(self):
        self.graph = Graph(nodes=[
            LoadOrCreateSession,
            GenerateSearchQueries,
            GetSavedContext,
            CollectWebData,
            PerformAIReview,
            UpdateSession,
            CheckCompletion,
            WipeSession,
            SaveSession,
            PopulateResult
        ])

    async def review(
        self,
        content: str,
        session_id: str,
        max_retries: int = 3,
        quality_threshold: float = 0.8
    ) -> ReviewResult:

        state = ReviewState(
            session_id=session_id,
            content=content,
            max_retries=max_retries,
            quality_threshold=quality_threshold
        )

        result = await self.graph.run(LoadOrCreateSession(), state=state)

        return result.output
