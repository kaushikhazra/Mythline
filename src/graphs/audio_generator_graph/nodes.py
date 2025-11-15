from __future__ import annotations

import os
import json
from pathlib import Path
from dataclasses import dataclass
from termcolor import colored

from pydantic_graph import BaseNode, End, GraphRunContext

from src.graphs.audio_generator_graph.models.state_models import AudioGeneratorSession
from src.agents.shot_creator_agent.models.output_models import Shot
from src.libs.audio import preprocess_text, normalize_audio, save_audio, ChatterboxModel
from src.libs.filesystem.file_operations import read_file, file_exists


def find_voice_file(actor: str) -> str | None:
    voices_dir = Path("voices")
    if not voices_dir.exists():
        return None

    for file in voices_dir.glob("*.wav"):
        if file.stem.lower() == actor.lower():
            return str(file)

    return None


@dataclass
class LoadShots(BaseNode[AudioGeneratorSession]):
    async def run(self, ctx: GraphRunContext[AudioGeneratorSession]) -> IdentifyActors | End[str]:
        subject = ctx.state.subject
        shots_file = f"output/{subject}/shots.json"

        print(colored(f"\n[*] Loading shots for {subject}...", "cyan"))

        if not file_exists(shots_file):
            error_msg = f"Shots file not found: {shots_file}"
            print(colored(f"[!] {error_msg}", "red"))
            print(colored(f"[!] Please run create_shots first", "red"))
            return End(error_msg)

        shots_content = read_file(shots_file)
        shots_data = json.loads(shots_content)
        ctx.state.shots = [Shot.model_validate(shot) for shot in shots_data]

        print(colored(f"[+] Loaded {len(ctx.state.shots)} shots", "green"))
        return IdentifyActors()


@dataclass
class IdentifyActors(BaseNode[AudioGeneratorSession]):
    async def run(self, ctx: GraphRunContext[AudioGeneratorSession]) -> CheckTemplates:
        print(colored(f"\n[*] Identifying unique actors...", "cyan"))

        actors = set()
        for shot in ctx.state.shots:
            actors.add(shot.actor)

        ctx.state.actors = sorted(list(actors))

        print(colored(f"[+] Found {len(ctx.state.actors)} unique actors: {', '.join(ctx.state.actors)}", "green"))
        return CheckTemplates()


@dataclass
class CheckTemplates(BaseNode[AudioGeneratorSession]):
    async def run(self, ctx: GraphRunContext[AudioGeneratorSession]) -> ListMissing | InitializeIndex:
        print(colored(f"\n[*] Checking voice templates...", "cyan"))

        missing_actors = []
        for actor in ctx.state.actors:
            voice_file = find_voice_file(actor)
            if voice_file is None:
                missing_actors.append(actor)

        if missing_actors:
            return ListMissing(missing_actors=missing_actors)

        print(colored(f"[+] All voice templates found", "green"))
        return InitializeIndex()


@dataclass
class ListMissing(BaseNode[AudioGeneratorSession]):
    missing_actors: list[str]

    async def run(self, ctx: GraphRunContext[AudioGeneratorSession]) -> End[str]:
        error_msg = f"Missing voice templates for: {', '.join(self.missing_actors)}"
        print(colored(f"\n[!] {error_msg}", "red"))
        print(colored(f"[!] Please create voice templates manually for these actors", "red"))
        return End(error_msg)


@dataclass
class InitializeIndex(BaseNode[AudioGeneratorSession]):
    async def run(self, ctx: GraphRunContext[AudioGeneratorSession]) -> CheckHasMore:
        ctx.state.shot_index = 0

        subject = ctx.state.subject
        audio_dir = f"output/{subject}/audio"
        os.makedirs(audio_dir, exist_ok=True)

        print(colored(f"\n[*] Initialized audio generation", "cyan"))
        return CheckHasMore()


@dataclass
class CheckHasMore(BaseNode[AudioGeneratorSession]):
    async def run(self, ctx: GraphRunContext[AudioGeneratorSession]) -> GetShot | End[str]:
        if ctx.state.shot_index < len(ctx.state.shots):
            return GetShot()

        print(colored(f"\n[+] Audio generation complete!", "green"))
        return End("Complete")


@dataclass
class GetShot(BaseNode[AudioGeneratorSession]):
    async def run(self, ctx: GraphRunContext[AudioGeneratorSession]) -> CheckAudioExists:
        ctx.state.current_shot = ctx.state.shots[ctx.state.shot_index]
        return CheckAudioExists()


@dataclass
class CheckAudioExists(BaseNode[AudioGeneratorSession]):
    async def run(self, ctx: GraphRunContext[AudioGeneratorSession]) -> IncrementIndex | PreProcess:
        subject = ctx.state.subject
        shot = ctx.state.current_shot
        audio_file = f"output/{subject}/audio/shot_{shot.shot_number}_{shot.actor}.wav"

        if file_exists(audio_file):
            print(colored(f"[~] Skipping shot {shot.shot_number} (audio exists)", "yellow"))
            return IncrementIndex()

        return PreProcess()


@dataclass
class PreProcess(BaseNode[AudioGeneratorSession]):
    async def run(self, ctx: GraphRunContext[AudioGeneratorSession]) -> GenerateAudio:
        text = ctx.state.current_shot.text
        ctx.state.preprocessed_text = preprocess_text(text)
        return GenerateAudio()


@dataclass
class GenerateAudio(BaseNode[AudioGeneratorSession]):
    async def run(self, ctx: GraphRunContext[AudioGeneratorSession]) -> PostProcess:
        shot = ctx.state.current_shot

        print(colored(f"\n[*] Generating audio for shot {shot.shot_number} - {shot.actor}", "cyan"))

        voice_path = find_voice_file(shot.actor)

        model = ChatterboxModel.get_instance()

        wav = model.generate(
            ctx.state.preprocessed_text,
            audio_prompt_path=voice_path,
            temperature=shot.temperature,
            exaggeration=shot.exaggeration,
            cfg_weight=shot.cfg_weight
        )

        ctx.state.raw_audio = wav
        return PostProcess()


@dataclass
class PostProcess(BaseNode[AudioGeneratorSession]):
    async def run(self, ctx: GraphRunContext[AudioGeneratorSession]) -> SaveAudio:
        raw_audio = ctx.state.raw_audio
        # ctx.state.processed_audio = normalize_audio(raw_audio, target_level=-20.0)
        ctx.state.processed_audio = raw_audio
        return SaveAudio()


@dataclass
class SaveAudio(BaseNode[AudioGeneratorSession]):
    async def run(self, ctx: GraphRunContext[AudioGeneratorSession]) -> IncrementIndex:
        subject = ctx.state.subject
        shot = ctx.state.current_shot
        output_path = f"output/{subject}/audio/shot_{shot.shot_number}_{shot.actor}.wav"

        sample_rate = ChatterboxModel.get_sample_rate()
        save_audio(output_path, ctx.state.processed_audio, sample_rate)

        print(colored(f"[+] Generated audio for shot {shot.shot_number} - {shot.actor}", "green"))
        return IncrementIndex()


@dataclass
class IncrementIndex(BaseNode[AudioGeneratorSession]):
    async def run(self, ctx: GraphRunContext[AudioGeneratorSession]) -> CheckHasMore:
        ctx.state.shot_index += 1

        total_shots = len(ctx.state.shots)
        current = ctx.state.shot_index
        print(colored(f"[*] Progress: {current}/{total_shots} audio files generated", "cyan"))

        return CheckHasMore()
