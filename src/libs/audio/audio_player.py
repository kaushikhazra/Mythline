import threading
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import sounddevice as sd
import soundfile as sf


class PlaybackState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass
class AudioPlayer:
    on_playback_complete: Callable[[], None] | None = None
    _state: PlaybackState = field(default=PlaybackState.STOPPED)
    _audio_data: np.ndarray | None = field(default=None, repr=False)
    _sample_rate: int = field(default=0)
    _position: int = field(default=0)
    _stream: sd.OutputStream | None = field(default=None, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def state(self) -> PlaybackState:
        with self._lock:
            return self._state

    def play(self, filepath: Path):
        with self._lock:
            self._stop_internal()

            audio, self._sample_rate = sf.read(str(filepath), dtype='float32')
            if len(audio.shape) > 1:
                audio = audio[:, 0]
            self._audio_data = audio

            self._position = 0
            self._state = PlaybackState.PLAYING
            self._start_stream()

    def _start_stream(self):
        def callback(outdata, frames, time_info, status):
            with self._lock:
                if self._state != PlaybackState.PLAYING or self._audio_data is None:
                    outdata.fill(0)
                    return

                end_pos = min(self._position + frames, len(self._audio_data))
                chunk = self._audio_data[self._position:end_pos]

                if len(chunk) < frames:
                    outdata[:len(chunk), 0] = chunk
                    outdata[len(chunk):] = 0
                    self._state = PlaybackState.STOPPED
                    self._position = 0
                    if self.on_playback_complete:
                        threading.Thread(target=self.on_playback_complete, daemon=True).start()
                else:
                    outdata[:, 0] = chunk

                self._position = end_pos

        self._stream = sd.OutputStream(
            samplerate=self._sample_rate,
            channels=1,
            callback=callback,
            blocksize=1024
        )
        self._stream.start()

    def pause(self):
        with self._lock:
            if self._state == PlaybackState.PLAYING:
                self._state = PlaybackState.PAUSED

    def resume(self):
        with self._lock:
            if self._state == PlaybackState.PAUSED:
                self._state = PlaybackState.PLAYING

    def stop(self):
        with self._lock:
            self._stop_internal()

    def _stop_internal(self):
        self._state = PlaybackState.STOPPED
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._position = 0
        self._audio_data = None
