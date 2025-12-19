# Voice Navigator Recording Commands

## Overview

Add voice commands to the voice navigator that control OBS Studio recording via WebSocket API.

## Implementation (OBS WebSocket)

Instead of simulating keystrokes (unreliable), we use OBS's built-in WebSocket server for direct control.

### Dependencies

- `obsws-python>=1.7.0` - OBS WebSocket client library

### OBS Setup

1. Open OBS Studio
2. Go to `Tools → WebSocket Server Settings`
3. Enable WebSocket server (default port: 4455)
4. Optionally set a password

## Voice Commands

| Voice Command | Action | Trigger Phrases |
|---------------|--------|-----------------|
| Start Recording | `client.start_record()` | "start recording", "begin recording" |
| Pause Recording | `client.pause_record()` | "pause recording" |
| Resume Recording | `client.resume_record()` | "resume recording", "continue recording" |
| Stop Recording | `client.stop_record()` | "stop recording", "end recording" |

## Files Created

- `src/libs/obs/__init__.py` - Module exports
- `src/libs/obs/controller.py` - OBSController class with connection handling

## Files Modified

- `requirements.txt` - Added `obsws-python>=1.7.0`
- `src/libs/voice/voice_commands.py` - Added recording command enums and patterns
- `src/ui/cli/voice_navigator.py` - Integrated OBSController

## Architecture

```
VoiceNavigator
├── VoiceRecognizer (speech-to-text)
├── AudioPlayer (WAV playback)
├── OBSController (recording control via WebSocket)
└── Rich Console (UI)
```

## Error Handling

- If OBS is not running or WebSocket not enabled: shows warning, recording commands disabled
- If recording action fails (e.g., already recording): shows appropriate feedback
- Graceful disconnect on navigator exit
