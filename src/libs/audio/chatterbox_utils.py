import os
import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS


def preprocess_text(text: str) -> str:
    """Preprocess text by removing or replacing special characters.

    Args:
        text: Input text to preprocess.

    Returns:
        Preprocessed text with special characters handled.
    """
    if not text:
        return text

    replacements = {
        "—": "; ",   # Em dash to semicolon
        "'": "'",    # Curly single quote to straight quote
        "…": "...",  # Ellipsis to three dots
        "*": ""      # Remove asterisks
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text.strip()


def normalize_audio(audio: torch.Tensor, target_level: float = -20.0) -> torch.Tensor:
    """Normalize audio to a target level in dBFS.

    Args:
        audio: Input audio tensor.
        target_level: Target level in dBFS.

    Returns:
        Normalized audio tensor.
    """
    if audio.numel() == 0:
        return audio

    rms = torch.sqrt(torch.mean(audio ** 2))

    if rms < 1e-6:
        return audio

    target_linear = 10 ** (target_level / 20.0)
    current_linear = rms
    scaling = target_linear / current_linear

    return torch.clamp(audio * scaling, -0.999, 0.999)


def save_audio(filepath: str, audio: torch.Tensor, sample_rate: int):
    """Save audio tensor to WAV file.

    Args:
        filepath: Path to save the audio file.
        audio: Audio tensor to save.
        sample_rate: Sample rate of the audio.
    """
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

    if len(audio.shape) == 1:
        audio = audio.unsqueeze(0)

    ta.save(filepath, audio, sample_rate)


class ChatterboxModel:
    _instance = None
    _sample_rate = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            cls._instance = ChatterboxTTS.from_pretrained(device=device)
            cls._sample_rate = cls._instance.sr
        return cls._instance

    @classmethod
    def get_sample_rate(cls):
        if cls._sample_rate is None:
            cls.get_instance()
        return cls._sample_rate
