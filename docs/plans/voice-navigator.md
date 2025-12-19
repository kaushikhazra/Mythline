# Voice-Controlled Audio Navigator

## Overview

Create a voice-controlled navigation system for playing shot audio files. Uses Vosk (offline speech recognition) and sounddevice for audio playback.

**Voice Commands:** start, next, again, previous, "go to N", pause, resume, stop

## Files to Create

| File | Purpose |
|------|---------|
| `src/libs/voice/__init__.py` | Export voice module |
| `src/libs/voice/voice_commands.py` | Command enum and parsing |
| `src/libs/voice/voice_recognizer.py` | Vosk-based speech recognition |
| `src/libs/audio/audio_player.py` | WAV playback with pause/resume/stop |
| `src/ui/cli/voice_navigator.py` | Main CLI (based on shot_director.py patterns) |
| `start_voice_navigator.bat` | Windows launcher |

## Files to Modify

| File | Change |
|------|--------|
| `requirements.txt` | Add: vosk, pyaudio, sounddevice, numpy |

## Dependencies

```
vosk>=0.3.45
pyaudio>=0.2.14
sounddevice>=0.4.6
numpy>=1.24.0
```

**Vosk Model:** Download `vosk-model-small-en-us` (~40MB) to `.mythline/vosk/models/` folder

## Architecture

```
VoiceNavigator (main class)
├── VoiceRecognizer (Vosk + PyAudio)
├── AudioPlayer (sounddevice)
└── Display (Rich console - reuse from shot_director.py)
```

**Key Design Decision:** Pause voice recognition during audio playback, resume when audio ends. This avoids speaker-to-mic feedback.

## Implementation Steps

### Step 1: Voice Command Module
Create `src/libs/voice/voice_commands.py`:
- `VoiceCommand` enum (START, NEXT, AGAIN, PREVIOUS, GO_TO, PAUSE, RESUME, STOP)
- `ParsedCommand` dataclass with optional shot_number
- `parse_command(text)` function with pattern matching

### Step 2: Voice Recognizer
Create `src/libs/voice/voice_recognizer.py`:
- Load Vosk model from `.mythline/vosk/models/vosk-model-small-en-us`
- Stream microphone input via PyAudio (16kHz, mono)
- Callback-based recognition with pause/resume capability

### Step 3: Audio Player
Create `src/libs/audio/audio_player.py`:
- `PlaybackState` enum (STOPPED, PLAYING, PAUSED)
- `AudioPlayer` class with play/pause/resume/stop
- Non-blocking playback using sounddevice callbacks
- `on_playback_complete` callback for resuming voice recognition

### Step 4: Voice Navigator CLI
Create `src/ui/cli/voice_navigator.py`:
- Reuse display patterns from `shot_director.py:63-128`
- Reuse progress save/load from `shot_director.py:35-46`
- Audio path: `output/{subject}/audio/shot_{N}_{actor}.wav`
- Command handler dispatches to play/next/prev/jump/pause/stop

### Step 5: Batch Launcher
Create `start_voice_navigator.bat`:
- Validate subject argument
- Run `python -m src.ui.cli.voice_navigator %1`

### Step 6: Update Dependencies
Add to `requirements.txt`: vosk, pyaudio, sounddevice, numpy

## Command Flow

```
User says "start"
  → VoiceRecognizer.pause_listening()
  → Display shot info
  → AudioPlayer.play(shot_audio.wav)
  → [audio finishes]
  → on_playback_complete callback
  → VoiceRecognizer.resume_listening()
  → Display "Listening..."
```

## Error Handling

- Missing audio file: Show warning, stay on current shot
- Invalid shot number: Show range warning
- Microphone error: Show setup instructions
- Vosk model not found: Show download URL

## Usage

```bash
start_voice_navigator.bat last_stand
```

Or directly:
```bash
python -m src.ui.cli.voice_navigator last_stand
```
