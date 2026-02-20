from pydantic_graph import Graph

from src.graphs.shot_creator_graph.models.state_models import ShotCreatorSession
from src.graphs.shot_creator_graph.nodes import (
    LoadStory,
    InitializeChunking,
    ProcessIntroduction,
    InitializeSegmentIndex,
    CheckHasMoreSegments,
    ProcessSegment,
    IncrementSegmentIndex,
    ProcessConclusion,
    InitializeShotIndex,
    CheckHasMoreChunks,
    GetChunk,
    CreateShot,
    StoreShot,
    WriteShotsFile,
    IncrementChunkIndex
)


class ShotCreatorGraph:
    def __init__(self, subject: str):
        self.subject = subject

        self.graph = Graph(
            nodes=[
                LoadStory,
                InitializeChunking,
                ProcessIntroduction,
                InitializeSegmentIndex,
                CheckHasMoreSegments,
                ProcessSegment,
                IncrementSegmentIndex,
                ProcessConclusion,
                InitializeShotIndex,
                CheckHasMoreChunks,
                GetChunk,
                CreateShot,
                StoreShot,
                WriteShotsFile,
                IncrementChunkIndex
            ]
        )

    async def run(self) -> None:
        state = ShotCreatorSession(subject=self.subject)
        await self.graph.run(LoadStory(), state=state)
