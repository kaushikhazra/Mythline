from pydantic_graph import Graph

from src.graphs.shot_creator_graph.models.state_models import ShotCreatorSession
from src.graphs.shot_creator_graph.nodes import (
    LoadStory,
    InitializeChunking,
    ProcessIntroduction,
    InitializeQuestIndex,
    CheckHasMoreQuests,
    GetNextQuest,
    ProcessQuestIntroduction,
    ProcessQuestDialogue,
    ProcessQuestExecution,
    ProcessQuestCompletion,
    IncrementQuestIndex,
    ProcessConclusion,
    InitializeShotIndex,
    CheckHasMoreChunks,
    GetChunk,
    CreateShot,
    ReviewShot,
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
                InitializeQuestIndex,
                CheckHasMoreQuests,
                GetNextQuest,
                ProcessQuestIntroduction,
                ProcessQuestDialogue,
                ProcessQuestExecution,
                ProcessQuestCompletion,
                IncrementQuestIndex,
                ProcessConclusion,
                InitializeShotIndex,
                CheckHasMoreChunks,
                GetChunk,
                CreateShot,
                ReviewShot,
                StoreShot,
                WriteShotsFile,
                IncrementChunkIndex
            ]
        )

    async def run(self) -> None:
        state = ShotCreatorSession(subject=self.subject)
        await self.graph.run(LoadStory(), state=state)
