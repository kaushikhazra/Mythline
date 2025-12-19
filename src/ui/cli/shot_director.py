import sys
import json
import time
import msvcrt
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout

console = Console()

ARROW_PREFIX = 224
LEFT_ARROW = 75
RIGHT_ARROW = 77
UP_ARROW = 72
DOWN_ARROW = 80


class ShotDirector:

    def __init__(self, subject: str):
        self.subject = subject
        self.shots = self.load_shots()
        self.current_index = self.load_progress()
        self.jump_buffer = ""

    def load_shots(self) -> list[dict]:
        path = Path(f"output/{self.subject}/shots.json")
        if not path.exists():
            console.print(f"[red]Error: shots.json not found at {path}[/red]")
            sys.exit(1)
        return json.loads(path.read_text(encoding="utf-8"))

    def load_progress(self) -> int:
        progress_path = Path(f"output/{self.subject}/.director_progress")
        if progress_path.exists():
            try:
                return int(progress_path.read_text().strip())
            except ValueError:
                return 0
        return 0

    def save_progress(self):
        progress_path = Path(f"output/{self.subject}/.director_progress")
        progress_path.write_text(str(self.current_index))

    def next_shot(self):
        if self.current_index < len(self.shots) - 1:
            self.current_index += 1
            self.save_progress()

    def prev_shot(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.save_progress()

    def jump_to(self, shot_number: int):
        if 1 <= shot_number <= len(self.shots):
            self.current_index = shot_number - 1
            self.save_progress()

    def display_shot(self):
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

        header_panel = Panel(
            Text.assemble(header_text, "\n", meta_text),
            title="[cyan bold]Shot Director[/cyan bold]",
            border_style="dim",
            padding=(0, 2)
        )
        console.print(header_panel)

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

        player_actions = shot.get('player_actions', 'N/A')
        console.print(Panel(
            Text(player_actions, style="white"),
            title="[cyan bold]Player Actions[/cyan bold]",
            border_style="dim",
            padding=(0, 2)
        ))

        backdrop = shot.get('backdrop', 'N/A')
        console.print(Panel(
            Text(backdrop, style="white"),
            title="[cyan bold]Backdrop[/cyan bold]",
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

        controls = Text()
        controls.append("  [", style="dim")
        controls.append("←", style="cyan")
        controls.append("] Previous  [", style="dim")
        controls.append("→", style="cyan")
        controls.append("] Next  [", style="dim")
        controls.append("number", style="cyan")
        controls.append("] Jump  [", style="dim")
        controls.append("q", style="cyan")
        controls.append("] Quit", style="dim")

        if self.jump_buffer:
            controls.append(f"   Jump to: {self.jump_buffer}_", style="yellow")

        console.print()
        console.print(controls)

    def run(self):
        console.print(f"\n[cyan]Loading shots for:[/cyan] [bold]{self.subject}[/bold]")
        console.print(f"[cyan]Total shots:[/cyan] [bold]{len(self.shots)}[/bold]")

        if self.current_index > 0:
            console.print(f"[green]Resuming from shot {self.current_index + 1}[/green]")

        console.print("\n[dim]Press any key to start...[/dim]")
        msvcrt.getch()

        self.display_shot()

        while True:
            time.sleep(0.05)

            if not msvcrt.kbhit():
                continue

            key = msvcrt.getch()

            if key == b'\xe0' or key == b'\x00':
                arrow = msvcrt.getch()
                arrow_code = ord(arrow)

                if arrow_code == RIGHT_ARROW or arrow_code == DOWN_ARROW:
                    self.jump_buffer = ""
                    self.next_shot()
                    self.display_shot()
                elif arrow_code == LEFT_ARROW or arrow_code == UP_ARROW:
                    self.jump_buffer = ""
                    self.prev_shot()
                    self.display_shot()
            else:
                char = key.decode('utf-8', errors='ignore')

                if char.lower() == 'q':
                    break

                if char.isdigit():
                    self.jump_buffer += char
                    self.display_shot()

                elif char == '\r' and self.jump_buffer:
                    try:
                        shot_num = int(self.jump_buffer)
                        self.jump_to(shot_num)
                    except ValueError:
                        pass
                    self.jump_buffer = ""
                    self.display_shot()

                elif char == '\x1b':
                    self.jump_buffer = ""
                    self.display_shot()

        console.clear()
        console.print(Panel(
            Text("Session saved. Good work!", style="bright_white"),
            title="[cyan bold]That's a wrap![/cyan bold]",
            border_style="green",
            padding=(1, 2)
        ))


def main():
    if len(sys.argv) < 2:
        console.print("[yellow]Usage:[/yellow] shot_director.py <subject>")
        console.print("[dim]Example: shot_director.py last_stand[/dim]")
        sys.exit(1)

    subject = sys.argv[1]
    director = ShotDirector(subject)
    director.run()


if __name__ == "__main__":
    main()
