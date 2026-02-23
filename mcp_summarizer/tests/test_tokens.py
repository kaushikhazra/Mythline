"""Unit tests for src/tokens.py — tiktoken cl100k_base wrappers."""

from src.tokens import count_tokens, decode, encode


def test_count_tokens_empty():
    assert count_tokens("") == 0


def test_count_tokens_single_word():
    tokens = count_tokens("hello")
    assert tokens == 1


def test_count_tokens_sentence():
    tokens = count_tokens("The quick brown fox jumps over the lazy dog.")
    assert tokens > 0


def test_count_tokens_returns_int():
    result = count_tokens("some text")
    assert isinstance(result, int)


def test_encode_returns_list_of_ints():
    result = encode("hello world")
    assert isinstance(result, list)
    assert all(isinstance(t, int) for t in result)


def test_encode_empty():
    assert encode("") == []


def test_decode_roundtrip():
    original = "The quick brown fox jumps over the lazy dog."
    tokens = encode(original)
    decoded = decode(tokens)
    assert decoded == original


def test_decode_empty():
    assert decode([]) == ""


def test_encode_decode_unicode():
    text = "Elwynn Forest — home of the Alliance"
    tokens = encode(text)
    assert decode(tokens) == text


def test_count_matches_encode_length():
    text = "This is a test of the token counting system."
    assert count_tokens(text) == len(encode(text))
