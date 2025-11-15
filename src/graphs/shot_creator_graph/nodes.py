from __future__ import annotations
import json
from dataclasses import dataclass
from termcolor import colored

from pydantic_graph import BaseNode, End, GraphRunContext

from src.graphs.shot_creator_graph.models.state_models import ShotCreatorSession
from src.agents.story_creator_agent.models.story_models import Story
from src.agents.chunker_agent import ChunkerAgent
from src.agents.shot_creator_agent import ShotCreatorAgent
from src.libs.filesystem.file_operations import read_file, write_file, file_exists


def extract_first_name(full_name: str) -> str:
    titles = ["Magistrix", "Ranger", "Arch", "Mage", "Huntress", "Priestess",
              "Lord", "Lady", "Captain", "Commander", "High", "Elder"]

    parts = full_name.split()
    filtered = [part for part in parts if part not in titles]
    return filtered[0] if filtered else full_name.split()[0]


@dataclass
class LoadStory(BaseNode[ShotCreatorSession]):
    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> InitializeChunking | End[str]:
        subject = ctx.state.subject
        story_file = f"output/{subject}/story.json"

        print(colored(f"\n[*] Loading story for {subject}...", "cyan"))

        if not file_exists(story_file):
            error_msg = f"Story file not found: {story_file}"
            print(colored(f"[!] {error_msg}", "red"))
            return End(error_msg)

        story_content = read_file(story_file)
        ctx.state.story = Story.model_validate_json(story_content)

        print(colored(f"[+] Story loaded", "green"))
        return InitializeChunking()


@dataclass
class InitializeChunking(BaseNode[ShotCreatorSession]):
    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> ProcessIntroduction | InitializeShotIndex:
        subject = ctx.state.subject
        shots_file = f"output/{subject}/shots.json"
        chunks_file = f"output/{subject}/chunks.json"

        ctx.state.chunks = []
        ctx.state.shots = []

        if file_exists(chunks_file):
            print(colored(f"\n[*] Found existing chunks.json, loading chunks...", "yellow"))
            chunks_content = read_file(chunks_file)
            try:
                chunks_data = json.loads(chunks_content)
                if chunks_data:
                    from src.agents.chunker_agent.models.output_models import Chunk
                    ctx.state.chunks = [Chunk(**chunk) for chunk in chunks_data]
                    print(colored(f"[+] Loaded {len(ctx.state.chunks)} chunks from {chunks_file}", "green"))
                    print(colored("[*] Skipping chunking phase (using existing chunks)", "yellow"))
                    return InitializeShotIndex()
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                print(colored(f"[!] Invalid chunks.json ({str(e)}), regenerating chunks...", "yellow"))

        if file_exists(shots_file):
            write_file(shots_file, "[]")

        print(colored("\n[*] Starting chunking phase...", "cyan"))
        return ProcessIntroduction()


@dataclass
class ProcessIntroduction(BaseNode[ShotCreatorSession]):
    def __post_init__(self):
        self.chunker_agent = None

    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> InitializeQuestIndex:
        if ctx.state.story.introduction is None:
            print(colored("[*] No introduction to process", "yellow"))
            return InitializeQuestIndex()

        if self.chunker_agent is None:
            self.chunker_agent = ChunkerAgent()

        print(colored("[*] Processing introduction...", "cyan"))

        result = await self.chunker_agent.run(
            text=ctx.state.story.introduction.text,
            chunk_type="narration",
            actor="aaryan",
            reference="Introduction"
        )

        ctx.state.chunks.extend(result.output)
        print(colored(f"[+] Created {len(result.output)} chunk(s) from introduction", "green"))

        return InitializeQuestIndex()


@dataclass
class InitializeQuestIndex(BaseNode[ShotCreatorSession]):
    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> CheckHasMoreQuests:
        ctx.state.quest_index = 0
        return CheckHasMoreQuests()


@dataclass
class CheckHasMoreQuests(BaseNode[ShotCreatorSession]):
    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> GetNextQuest | ProcessConclusion:
        if ctx.state.quest_index < len(ctx.state.story.quests):
            return GetNextQuest()
        else:
            return ProcessConclusion()


@dataclass
class GetNextQuest(BaseNode[ShotCreatorSession]):
    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> ProcessQuestIntroduction:
        ctx.state.current_quest = ctx.state.story.quests[ctx.state.quest_index]
        quest_num = ctx.state.quest_index + 1
        print(colored(f"\n[*] Processing quest {quest_num}: {ctx.state.current_quest.title}", "cyan"))
        return ProcessQuestIntroduction()


@dataclass
class ProcessQuestIntroduction(BaseNode[ShotCreatorSession]):
    def __post_init__(self):
        self.chunker_agent = None

    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> ProcessQuestDialogue:
        if ctx.state.current_quest.sections.introduction is None:
            return ProcessQuestDialogue()

        if self.chunker_agent is None:
            self.chunker_agent = ChunkerAgent()

        quest_num = ctx.state.quest_index + 1
        reference = f"Quest {quest_num} - Introduction"

        result = await self.chunker_agent.run(
            text=ctx.state.current_quest.sections.introduction.text,
            chunk_type="narration",
            actor="aaryan",
            reference=reference
        )

        ctx.state.chunks.extend(result.output)
        print(colored(f"[+] Created {len(result.output)} chunk(s) from quest introduction", "green"))

        return ProcessQuestDialogue()


@dataclass
class ProcessQuestDialogue(BaseNode[ShotCreatorSession]):
    def __post_init__(self):
        self.chunker_agent = None

    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> ProcessQuestExecution:
        if ctx.state.current_quest.sections.dialogue is None:
            return ProcessQuestExecution()

        if self.chunker_agent is None:
            self.chunker_agent = ChunkerAgent()

        quest_num = ctx.state.quest_index + 1
        reference = f"Quest {quest_num} - Dialogue"
        chunk_count = 0

        for line in ctx.state.current_quest.sections.dialogue.lines:
            actor_first_name = extract_first_name(line.actor)

            result = await self.chunker_agent.run(
                text=line.line,
                chunk_type="dialogue",
                actor=actor_first_name,
                reference=reference
            )

            ctx.state.chunks.extend(result.output)
            chunk_count += len(result.output)

        print(colored(f"[+] Created {chunk_count} chunk(s) from quest dialogue", "green"))
        return ProcessQuestExecution()


@dataclass
class ProcessQuestExecution(BaseNode[ShotCreatorSession]):
    def __post_init__(self):
        self.chunker_agent = None

    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> ProcessQuestCompletion:
        if ctx.state.current_quest.sections.execution is None:
            return ProcessQuestCompletion()

        if self.chunker_agent is None:
            self.chunker_agent = ChunkerAgent()

        quest_num = ctx.state.quest_index + 1
        reference = f"Quest {quest_num} - Execution"

        result = await self.chunker_agent.run(
            text=ctx.state.current_quest.sections.execution.text,
            chunk_type="narration",
            actor="aaryan",
            reference=reference
        )

        ctx.state.chunks.extend(result.output)
        print(colored(f"[+] Created {len(result.output)} chunk(s) from quest execution", "green"))

        return ProcessQuestCompletion()


@dataclass
class ProcessQuestCompletion(BaseNode[ShotCreatorSession]):
    def __post_init__(self):
        self.chunker_agent = None

    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> IncrementQuestIndex:
        if ctx.state.current_quest.sections.completion is None:
            return IncrementQuestIndex()

        if self.chunker_agent is None:
            self.chunker_agent = ChunkerAgent()

        quest_num = ctx.state.quest_index + 1
        reference = f"Quest {quest_num} - Completion"
        chunk_count = 0

        for line in ctx.state.current_quest.sections.completion.lines:
            actor_first_name = extract_first_name(line.actor)

            result = await self.chunker_agent.run(
                text=line.line,
                chunk_type="dialogue",
                actor=actor_first_name,
                reference=reference
            )

            ctx.state.chunks.extend(result.output)
            chunk_count += len(result.output)

        print(colored(f"[+] Created {chunk_count} chunk(s) from quest completion", "green"))
        return IncrementQuestIndex()


@dataclass
class IncrementQuestIndex(BaseNode[ShotCreatorSession]):
    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> CheckHasMoreQuests:
        ctx.state.quest_index += 1
        return CheckHasMoreQuests()


@dataclass
class ProcessConclusion(BaseNode[ShotCreatorSession]):
    def __post_init__(self):
        self.chunker_agent = None

    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> InitializeShotIndex:
        if ctx.state.story.conclusion is None:
            print(colored("[*] No conclusion to process", "yellow"))
            return InitializeShotIndex()

        if self.chunker_agent is None:
            self.chunker_agent = ChunkerAgent()

        print(colored("\n[*] Processing conclusion...", "cyan"))

        result = await self.chunker_agent.run(
            text=ctx.state.story.conclusion.text,
            chunk_type="narration",
            actor="aaryan",
            reference="Conclusion"
        )

        ctx.state.chunks.extend(result.output)
        print(colored(f"[+] Created {len(result.output)} chunk(s) from conclusion", "green"))

        return InitializeShotIndex()


@dataclass
class InitializeShotIndex(BaseNode[ShotCreatorSession]):
    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> CheckHasMoreChunks:
        total_chunks = len(ctx.state.chunks)
        subject = ctx.state.subject

        chunks_file = f"output/{subject}/chunks.json"
        shots_file = f"output/{subject}/shots.json"

        chunks_data = [chunk.model_dump() for chunk in ctx.state.chunks]
        chunks_json = json.dumps(chunks_data, indent=2)
        write_file(chunks_file, chunks_json)

        print(colored(f"[+] Saved {total_chunks} chunks to {chunks_file}", "green"))

        if file_exists(shots_file):
            existing_shots_content = read_file(shots_file)
            try:
                existing_shots_data = json.loads(existing_shots_content)
                if existing_shots_data:
                    from src.agents.shot_creator_agent.models.output_models import Shot
                    ctx.state.shots = [Shot.model_validate(shot) for shot in existing_shots_data]
                    ctx.state.current_index = len(ctx.state.shots)
                    print(colored(f"[*] Resuming from shot {ctx.state.current_index + 1} ({len(ctx.state.shots)} shots already created)", "yellow"))
                else:
                    ctx.state.current_index = 0
            except (json.JSONDecodeError, ValueError):
                ctx.state.current_index = 0
                print(colored(f"[!] Invalid shots.json, starting from beginning", "yellow"))
        else:
            ctx.state.current_index = 0

        remaining_chunks = total_chunks - ctx.state.current_index
        print(colored(f"\n[*] Starting shot creation phase ({remaining_chunks} chunks remaining)...", "cyan"))
        return CheckHasMoreChunks()


@dataclass
class CheckHasMoreChunks(BaseNode[ShotCreatorSession]):
    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> GetChunk | End[str]:
        if ctx.state.current_index < len(ctx.state.chunks):
            return GetChunk()
        else:
            total_shots = len(ctx.state.shots)
            print(colored(f"\n[+] Shot creation complete! Created {total_shots} shots", "green"))
            return End(f"Created {total_shots} shots")


@dataclass
class GetChunk(BaseNode[ShotCreatorSession]):
    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> CreateShot:
        return CreateShot()


@dataclass
class CreateShot(BaseNode[ShotCreatorSession]):
    def __post_init__(self):
        self.shot_creator_agent = None

    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> StoreShot:
        if self.shot_creator_agent is None:
            self.shot_creator_agent = ShotCreatorAgent()

        chunk = ctx.state.chunks[ctx.state.current_index]

        result = await self.shot_creator_agent.run(
            text=chunk.text,
            actor=chunk.actor,
            chunk_type=chunk.chunk_type,
            reference=chunk.reference
        )

        return StoreShot(shot=result.output)


@dataclass
class StoreShot(BaseNode[ShotCreatorSession]):
    shot: object

    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> WriteShotsFile:
        shot_number = ctx.state.current_index + 1
        self.shot.shot_number = shot_number
        ctx.state.shots.append(self.shot)
        return WriteShotsFile()


@dataclass
class WriteShotsFile(BaseNode[ShotCreatorSession]):
    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> IncrementChunkIndex:
        subject = ctx.state.subject
        shots_file = f"output/{subject}/shots.json"

        shots_data = [shot.model_dump() for shot in ctx.state.shots]
        shots_json = json.dumps(shots_data, indent=2)
        write_file(shots_file, shots_json)

        return IncrementChunkIndex()


@dataclass
class IncrementChunkIndex(BaseNode[ShotCreatorSession]):
    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> CheckHasMoreChunks:
        ctx.state.current_index += 1

        print(colored(f"[*] Progress: {ctx.state.current_index}/{len(ctx.state.chunks)} shots created", "cyan"))

        return CheckHasMoreChunks()
