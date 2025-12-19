import json
import threading
from pathlib import Path
from typing import Callable

from vosk import Model, KaldiRecognizer
import pyaudio

VOICE_GRAMMAR = [
    "start", "play", "begin",
    "next", "forward",
    "previous", "back",
    "again", "repeat", "replay",
    "pause", "wait", "hold",
    "resume", "continue",
    "stop", "quit", "exit", "end",
    "go to", "jump to", "shot",
    "start recording", "begin recording", "start record",
    "pause recording", "post recording", "hold recording", "pause record",
    "resume recording", "continue recording", "resume record",
    "stop recording", "end recording", "stop record",
    "one", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
    "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
    "hundred",
    "[unk]",
]


class VoiceRecognizer:
    SAMPLE_RATE = 16000
    CHUNK_SIZE = 4000
    DEFAULT_MODEL_PATH = ".mythline/vosk/models/vosk-model-small-en-us"

    def __init__(self, model_path: str | None = None, use_grammar: bool = True):
        if model_path:
            self._model_path = Path(model_path)
        else:
            project_root = Path(__file__).parent.parent.parent.parent
            self._model_path = project_root / self.DEFAULT_MODEL_PATH
        if not self._model_path.exists():
            raise FileNotFoundError(
                f"Vosk model not found at {self._model_path}. "
                "Download from https://alphacephei.com/vosk/models"
            )
        self._model = Model(str(self._model_path))
        if use_grammar:
            grammar_json = json.dumps(VOICE_GRAMMAR)
            self._recognizer = KaldiRecognizer(self._model, self.SAMPLE_RATE, grammar_json)
        else:
            self._recognizer = KaldiRecognizer(self._model, self.SAMPLE_RATE)
        self._audio = pyaudio.PyAudio()
        self._stream = None
        self._is_listening = False
        self._is_running = False
        self._lock = threading.Lock()

    def start_listening(self, on_command: Callable[[str], None]):
        self._stream = self._audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.SAMPLE_RATE,
            input=True,
            frames_per_buffer=self.CHUNK_SIZE
        )

        self._is_running = True
        self._is_listening = True

        while self._is_running:
            with self._lock:
                if not self._is_listening:
                    continue

            try:
                data = self._stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
            except OSError:
                continue

            with self._lock:
                if not self._is_listening:
                    continue

            if self._recognizer.AcceptWaveform(data):
                result = json.loads(self._recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    on_command(text)

    def pause_listening(self):
        with self._lock:
            self._is_listening = False

    def resume_listening(self):
        with self._lock:
            self._is_listening = True

    def stop(self):
        self._is_running = False
        self._is_listening = False
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        self._audio.terminate()

    @property
    def is_listening(self) -> bool:
        with self._lock:
            return self._is_listening
