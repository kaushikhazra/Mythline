from __future__ import annotations
import json
from dataclasses import dataclass
from termcolor import colored

from pydantic_graph import BaseNode, End, GraphRunContext

from src.graphs.shot_creator_graph.models.state_models import ShotCreatorSession
from src.agents.story_creator_agent.models.story_models import Story
from src.agents.chunker_agent import ChunkerAgent
from src.agents.shot_creator_agent import ShotCreatorAgent
from src.agents.shot_reviewer_agent import ShotReviewerAgent
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
    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> ProcessIntroduction:
        subject = ctx.state.subject
        shots_file = f"output/{subject}/shots.json"

        ctx.state.chunks = []
        ctx.state.shots = []

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

    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> ReviewShot:
        if self.shot_creator_agent is None:
            self.shot_creator_agent = ShotCreatorAgent()

        chunk = ctx.state.chunks[ctx.state.current_index]

        text = chunk.text
        if ctx.state.current_review_comments:
            text += f"\n\n[REVIEW FEEDBACK - Address these issues]: {ctx.state.current_review_comments}"

        result = await self.shot_creator_agent.run(
            text=text,
            actor=chunk.actor,
            chunk_type=chunk.chunk_type,
            reference=chunk.reference
        )

        return ReviewShot(shot=result.output)


@dataclass
class ReviewShot(BaseNode[ShotCreatorSession]):
    shot: object

    def __post_init__(self):
        self.shot_reviewer_agent = None

    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> CreateShot | StoreShot:
        if self.shot_reviewer_agent is None:
            self.shot_reviewer_agent = ShotReviewerAgent(session_id=ctx.state.subject)

        shot_number = len(ctx.state.shots) + 1

        print(colored(f"\n[*] Reviewing shot {shot_number}...", "cyan"))

        previous_shots_context = ""
        if ctx.state.shots:
            same_location_shots = [s for s in ctx.state.shots if s.reference == self.shot.reference]
            if same_location_shots:
                previous_shots_context = f"\n\nPrevious shots in same location ({self.shot.reference}): {len(same_location_shots)} shots"

        review_prompt = f"""Review this WoW video shot for authenticity and feasibility.

Shot Details:
- Text: "{self.shot.text}"
- Actor: {self.shot.actor}
- Reference: {self.shot.reference}
- Camera Zoom: {self.shot.camera_zoom}
- Camera Angle: {self.shot.camera_angle}
- Player Actions: "{self.shot.player_actions}"
- Backdrop: "{self.shot.backdrop}"
- Duration: {self.shot.duration_seconds} seconds{previous_shots_context}

Check:
1. Backdrop matches WoW location "{self.shot.reference}"
2. Camera angle {self.shot.camera_angle} is achievable in WoW
3. Player actions describe only player character (no NPC control)
4. All emotes are valid WoW emotes
5. Backdrop uses WoW-appropriate terminology
6. Duration is reasonable for text length and actions
7. Player actions are concise (1-2 sentences max)
8. Backdrop description is succinct (1-2 sentences max)
9. Consistency with previous shots in same location"""

        review = await self.shot_reviewer_agent.run(review_prompt)

        print(colored(f"[+] Review score: {review.score:.2f}/1.0", "green" if review.score >= 0.8 else "yellow"))

        if review.need_improvement and ctx.state.current_retry_count < 3:
            ctx.state.current_retry_count += 1
            ctx.state.current_review_comments = review.review_comments
            print(colored(f"[!] Retry {ctx.state.current_retry_count}/3: {review.review_comments}", "yellow"))
            return CreateShot()
        else:
            if ctx.state.current_retry_count >= 3:
                print(colored(f"[!] Max retries reached, proceeding with score {review.score:.2f}", "yellow"))

            ctx.state.current_retry_count = 0
            ctx.state.current_review_comments = None
            return StoreShot(shot=self.shot)


@dataclass
class StoreShot(BaseNode[ShotCreatorSession]):
    shot: object

    async def run(self, ctx: GraphRunContext[ShotCreatorSession]) -> WriteShotsFile:
        shot_number = len(ctx.state.shots) + 1
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
