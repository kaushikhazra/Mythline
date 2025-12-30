# Deterministic Director CLI Plan

Replace the LLM-based Video Director with a simple, deterministic CLI that navigates through shots.json using arrow keys.

## Problem

The current `VideoDirector` agent uses an LLM to:
1. Read shots.json
2. Format and display shot information
3. Track progress

This is unnecessary - all direction data already exists in shots.json. The LLM adds:
- Cost per interaction
- Latency (API calls)
- Non-determinism (varying output format)
- Dependency on internet/API

## Solution

A simple Python CLI that:
1. Loads shots.json
2. Displays shots in a formatted template
3. Navigates with arrow keys
4. Jumps to specific shot by number
5. Saves/resumes progress

## User Interface

Clean terminal UI with color-coded sections (no emojis):

```
╭─ Shot Director ─────────────────────────────────────────────────╮
│                                                                 │
│  Shot 1 / 80                                        last_stand  │
│  Reference: Introduction                                        │
│  Actor: aaryan                          Duration: 21.0s         │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯

╭─ Camera ────────────────────────────────────────────────────────╮
│  Zoom: wide                                                     │
│  Angle: front                                                   │
╰─────────────────────────────────────────────────────────────────╯

╭─ Player Actions ────────────────────────────────────────────────╮
│  Stand at the threshold of Eversong Woods, face into the        │
│  golden canopy.                                                 │
╰─────────────────────────────────────────────────────────────────╯

╭─ Backdrop ──────────────────────────────────────────────────────╮
│  Eversong Woods where lantern-like golden groves meet the       │
│  ashen Dead Scar; distant Sunwell glow and rune-carved          │
│  runestones create a luminous, haunted atmosphere.              │
╰─────────────────────────────────────────────────────────────────╯

╭─ Text ──────────────────────────────────────────────────────────╮
│  "The road into Eversong Woods seemed to exhale as Sarephine    │
│  crossed its threshold. Gold light pooled between slender       │
│  trunks, leaves chiming with a sorcerous hush..."               │
╰─────────────────────────────────────────────────────────────────╯

  [←] Previous  [→] Next  [number] Jump  [q] Quit
```

### Color Scheme (Rich styling)

| Element | Color | Style |
|---------|-------|-------|
| Panel borders | `dim` | Rounded corners |
| Section titles | `cyan` | Bold |
| Shot number | `bright_white` | Bold |
| Labels (Zoom, Angle, etc.) | `dim white` | Regular |
| Values | `white` | Regular |
| Text content | `bright_white` | Italic |
| Key hints | `dim cyan` | Regular |
| Progress indicator | `green` | When complete |

## Controls

| Key | Action |
|-----|--------|
| `→` or `↓` | Next shot |
| `←` or `↑` | Previous shot |
| `0-9` then Enter | Jump to shot number |
| `q` | Quit and save progress |
| `m` | Mark shot as complete (optional) |

## Technical Implementation

### File Structure

```
src/ui/cli/
├── shot_director.py      # New deterministic director CLI
```

### Dependencies

- `curses` (Unix) or `windows-curses` (Windows) for terminal UI
- Alternative: `rich` library for cross-platform styled output with `keyboard` for input
- Simplest: `questionary` or basic input() with ANSI escape codes

### Recommended Approach: Rich + Keyboard

Use `rich` for beautiful terminal output and `keyboard` or simple input for navigation.

```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
```

### Core Logic

```python
class ShotDirector:
    def __init__(self, subject: str):
        self.subject = subject
        self.shots = self.load_shots()
        self.current_index = self.load_progress()

    def load_shots(self) -> list[dict]:
        path = Path(f"output/{self.subject}/shots.json")
        return json.loads(path.read_text())

    def load_progress(self) -> int:
        progress_path = Path(f"output/{self.subject}/.director_progress")
        if progress_path.exists():
            return int(progress_path.read_text())
        return 0

    def save_progress(self):
        progress_path = Path(f"output/{self.subject}/.director_progress")
        progress_path.write_text(str(self.current_index))

    def display_shot(self, shot: dict):
        # Format and display using rich
        pass

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

    def run(self):
        # Main loop with keyboard handling
        pass
```

### CLI Entry Point

```bash
python -m src.ui.cli.shot_director --subject last_stand
```

Or with argument parser:
```bash
python -m src.ui.cli.shot_director last_stand
```

### Progress Persistence

Save current shot index to `output/{subject}/.director_progress`:
- Simple text file with shot index
- Auto-save on navigation
- Resume on next run

## Implementation Steps

- [ ] 1. Create `src/ui/cli/shot_director.py`
- [ ] 2. Implement shot loading from `output/{subject}/shots.json`
- [ ] 3. Implement display formatting with `rich`
- [ ] 4. Implement arrow key navigation
- [ ] 5. Implement number input for jump-to-shot
- [ ] 6. Implement progress save/load
- [ ] 7. Add CLI argument parsing (subject name)
- [ ] 8. Test with `last_stand` shots

## Future Enhancements (Optional)

- [ ] Shot completion marking (checkbox per shot)
- [ ] Filter view (show only incomplete shots)
- [ ] Audio playback integration (play TTS while displaying shot)
- [ ] Export to checklist format
- [ ] Split-screen with audio waveform

## Files to Deprecate

After this is complete, the LLM-based director can be deprecated:
- `src/agents/video_director_agent/` - No longer needed
- `src/ui/cli/direct_shots.py` - Replace with new CLI

## Success Criteria

- [ ] Navigate 80 shots with arrow keys smoothly
- [ ] Jump to any shot by number
- [ ] Progress persists between sessions
- [ ] Zero LLM calls
- [ ] Instant response time
- [ ] Works offline
