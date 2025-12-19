import json
import threading
from pathlib import Path
from typing import Callable

from vosk import Model, KaldiRecognizer
import pyaudio


class VoiceRecognizer:
    SAMPLE_RATE = 16000
    CHUNK_SIZE = 8000
    DEFAULT_MODEL_PATH = ".mythline/vosk/models/vosk-model-small-en-us"

    def __init__(self, model_path: str | None = None):
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
