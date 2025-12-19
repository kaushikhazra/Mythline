import sys
import json
import threading
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.libs.voice import VoiceRecognizer, VoiceCommand, parse_command
from src.libs.audio.audio_player import AudioPlayer, PlaybackState
from src.libs.obs import OBSController

console = Console()


class VoiceNavigator:

    def __init__(self, subject: str):
        self.subject = subject
        self.shots = self._load_shots()
        self.current_index = self._load_progress()
        self._audio_player = AudioPlayer(on_playback_complete=self._on_audio_complete)
        self._voice_recognizer = None
        self._obs = OBSController()
        self._running = False
        self._display_lock = threading.Lock()

    def _load_shots(self) -> list[dict]:
        path = Path(f"output/{self.subject}/shots.json")
        if not path.exists():
            console.print(f"[red]Error: shots.json not found at {path}[/red]")
            sys.exit(1)
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_progress(self) -> int:
        progress_path = Path(f"output/{self.subject}/.director_progress")
        if progress_path.exists():
            try:
                return int(progress_path.read_text().strip())
            except ValueError:
                return 0
        return 0

    def _save_progress(self):
        progress_path = Path(f"output/{self.subject}/.director_progress")
        progress_path.write_text(str(self.current_index))

    def _get_audio_path(self, shot: dict) -> Path:
        shot_num = shot["shot_number"]
        actor = shot["actor"]
        return Path(f"output/{self.subject}/audio/shot_{shot_num}_{actor}.wav")

    def _on_audio_complete(self):
        if self._voice_recognizer:
            self._voice_recognizer.resume_listening()
        with self._display_lock:
            self._display_listening_indicator()

    def _handle_command(self, text: str):
        parsed = parse_command(text)

        with self._display_lock:
            console.print(f"[dim]Heard: {text}[/dim]")

        if parsed.command == VoiceCommand.START:
            self._play_current()
        elif parsed.command == VoiceCommand.NEXT:
            self._next_shot()
        elif parsed.command == VoiceCommand.PREVIOUS:
            self._prev_shot()
        elif parsed.command == VoiceCommand.AGAIN:
            self._play_current()
        elif parsed.command == VoiceCommand.GO_TO:
            if parsed.shot_number:
                self._jump_to(parsed.shot_number)
        elif parsed.command == VoiceCommand.PAUSE:
            self._audio_player.pause()
            with self._display_lock:
                console.print("[yellow]Paused[/yellow]")
        elif parsed.command == VoiceCommand.RESUME:
            self._audio_player.resume()
            with self._display_lock:
                console.print("[green]Resumed[/green]")
        elif parsed.command == VoiceCommand.STOP:
            self._stop()
        elif parsed.command == VoiceCommand.START_RECORDING:
            self._start_recording()
        elif parsed.command == VoiceCommand.PAUSE_RECORDING:
            self._pause_recording()
        elif parsed.command == VoiceCommand.RESUME_RECORDING:
            self._resume_recording()
        elif parsed.command == VoiceCommand.STOP_RECORDING:
            self._stop_recording()

    def _play_current(self):
        shot = self.shots[self.current_index]
        audio_path = self._get_audio_path(shot)

        if not audio_path.exists():
            with self._display_lock:
                console.print(f"[yellow]Audio missing: {audio_path.name}[/yellow]")
                self._display_listening_indicator()
            return

        if self._voice_recognizer:
            self._voice_recognizer.pause_listening()

        with self._display_lock:
            self._display_shot()
            self._display_playing_indicator()

        self._audio_player.play(audio_path)

    def _next_shot(self):
        if self.current_index < len(self.shots) - 1:
            self.current_index += 1
            self._save_progress()
            self._play_current()
        else:
            with self._display_lock:
                console.print("[yellow]Already at last shot[/yellow]")

    def _prev_shot(self):
        if self.current_index > 0:
            self.current_index -= 1
            self._save_progress()
            self._play_current()
        else:
            with self._display_lock:
                console.print("[yellow]Already at first shot[/yellow]")

    def _jump_to(self, shot_number: int):
        if 1 <= shot_number <= len(self.shots):
            self.current_index = shot_number - 1
            self._save_progress()
            self._play_current()
        else:
            with self._display_lock:
                console.print(f"[yellow]Invalid shot {shot_number} (1-{len(self.shots)})[/yellow]")

    def _stop(self):
        self._audio_player.stop()
        if self._voice_recognizer:
            self._voice_recognizer.stop()
        self._obs.disconnect()
        self._running = False

    def _start_recording(self):
        if self._obs.start_recording():
            with self._display_lock:
                console.print("[red bold]● Recording started[/red bold]")
        else:
            with self._display_lock:
                console.print("[yellow]Recording already active or OBS not connected[/yellow]")

    def _pause_recording(self):
        success, error = self._obs.pause_recording()
        if success:
            with self._display_lock:
                console.print("[yellow]⏸ Recording paused[/yellow]")
        else:
            with self._display_lock:
                console.print(f"[yellow]Cannot pause: {error}[/yellow]")

    def _resume_recording(self):
        success, error = self._obs.resume_recording()
        if success:
            with self._display_lock:
                console.print("[green]▶ Recording resumed[/green]")
        else:
            with self._display_lock:
                console.print(f"[yellow]Cannot resume: {error}[/yellow]")

    def _stop_recording(self):
        if self._obs.stop_recording():
            with self._display_lock:
                console.print("[dim]■ Recording stopped[/dim]")
        else:
            with self._display_lock:
                console.print("[yellow]Not recording or OBS not connected[/yellow]")

    def _display_shot(self):
        console.clear()
        shot = self.shots[self.current_index]
        total = len(self.shots)
        current = self.current_index + 1

        header_text = Text()
        header_text.append(f"Shot {current}", style="bold bright_white")
        header_text.append(f" / {total}", style="dim")
        header_text.append(f"{'':>40}", style="")
        header_text.append(f"{self.subject}", style="cyan")

        meta_text = Text()
        meta_text.append(f"Reference: ", style="dim")
        meta_text.append(f"{shot.get('reference', 'N/A')}\n", style="white")
        meta_text.append(f"Actor: ", style="dim")
        meta_text.append(f"{shot.get('actor', 'N/A')}", style="white")
        meta_text.append(f"{'':>30}", style="")
        meta_text.append(f"Duration: ", style="dim")
        meta_text.append(f"{shot.get('duration_seconds', 0)}s", style="white")

        console.print(Panel(
            Text.assemble(header_text, "\n", meta_text),
            title="[cyan bold]Voice Navigator[/cyan bold]",
            border_style="dim",
            padding=(0, 2)
        ))

        camera_text = Text()
        camera_text.append("Zoom: ", style="dim")
        camera_text.append(f"{shot.get('camera_zoom', 'N/A')}", style="white")
        camera_text.append("\n")
        camera_text.append("Angle: ", style="dim")
        camera_text.append(f"{shot.get('camera_angle', 'N/A')}", style="white")

        console.print(Panel(
            camera_text,
            title="[cyan bold]Camera[/cyan bold]",
            border_style="dim",
            padding=(0, 2)
        ))

        narration = shot.get('text', 'N/A')
        console.print(Panel(
            Text(f'"{narration}"', style="italic bright_white"),
            title="[cyan bold]Text[/cyan bold]",
            border_style="dim",
            padding=(0, 2)
        ))

    def _display_listening_indicator(self):
        console.print("\n[green]Listening...[/green] Say: start, next, previous, again, go to N, pause, stop")
        console.print("[dim]Recording: start/pause/resume/stop recording[/dim]")

    def _display_playing_indicator(self):
        console.print("\n[cyan]Playing...[/cyan]")

    def run(self):
        console.print(f"\n[cyan]Loading shots for:[/cyan] [bold]{self.subject}[/bold]")
        console.print(f"[cyan]Total shots:[/cyan] [bold]{len(self.shots)}[/bold]")

        if self.current_index > 0:
            console.print(f"[green]Resuming from shot {self.current_index + 1}[/green]")

        if self._obs.connect():
            console.print("[green]OBS connected[/green]")
        else:
            console.print("[yellow]OBS not available - recording commands disabled[/yellow]")
            console.print("[dim]Enable WebSocket server in OBS: Tools → WebSocket Server Settings[/dim]")

        console.print("\n[dim]Voice commands: start, next, previous, again, go to N, pause, stop[/dim]")
        console.print("[dim]Recording: start/pause/resume/stop recording[/dim]")
        console.print("[dim]Press Ctrl+C to exit[/dim]\n")

        try:
            self._voice_recognizer = VoiceRecognizer()
        except FileNotFoundError as e:
            console.print(f"[red]{e}[/red]")
            sys.exit(1)
        except OSError as e:
            console.print(f"[red]Microphone error: {e}[/red]")
            console.print("[dim]Ensure microphone is connected and accessible[/dim]")
            sys.exit(1)

        self._running = True
        self._display_shot()
        self._display_listening_indicator()

        try:
            self._voice_recognizer.start_listening(self._handle_command)
        except KeyboardInterrupt:
            self._stop()

        console.clear()
        console.print(Panel(
            Text("Session saved. Good work!", style="bright_white"),
            title="[cyan bold]That's a wrap![/cyan bold]",
            border_style="green",
            padding=(1, 2)
        ))


def main():
    if len(sys.argv) < 2:
        console.print("[yellow]Usage:[/yellow] voice_navigator.py <subject>")
        console.print("[dim]Example: voice_navigator.py last_stand[/dim]")
        sys.exit(1)

    subject = sys.argv[1]
    navigator = VoiceNavigator(subject)
    navigator.run()


if __name__ == "__main__":
    main()
