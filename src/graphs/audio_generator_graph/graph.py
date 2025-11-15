from pydantic_graph import Graph

from src.graphs.audio_generator_graph.models.state_models import AudioGeneratorSession
from src.graphs.audio_generator_graph.nodes import (
    LoadShots,
    IdentifyActors,
    CheckTemplates,
    ListMissing,
    InitializeIndex,
    CheckHasMore,
    GetShot,
    CheckAudioExists,
    PreProcess,
    GenerateAudio,
    PostProcess,
    SaveAudio,
    IncrementIndex
)


class AudioGeneratorGraph:
    def __init__(self, subject: str):
        self.subject = subject

        self.graph = Graph(
            nodes=[
                LoadShots,
                IdentifyActors,
                CheckTemplates,
                ListMissing,
                InitializeIndex,
                CheckHasMore,
                GetShot,
                CheckAudioExists,
                PreProcess,
                GenerateAudio,
                PostProcess,
                SaveAudio,
                IncrementIndex
            ]
        )

    async def run(self) -> None:
        state = AudioGeneratorSession(subject=self.subject)
        await self.graph.run(LoadShots(), state=state)
