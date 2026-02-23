"""Token counting and encoding via tiktoken (cl100k_base)."""

import tiktoken

_encoding = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens using cl100k_base encoding."""
    return len(_encoding.encode(text))


def encode(text: str) -> list[int]:
    """Encode text to token IDs."""
    return _encoding.encode(text)


def decode(tokens: list[int]) -> str:
    """Decode token IDs to text."""
    return _encoding.decode(tokens)
