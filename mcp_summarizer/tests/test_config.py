"""Unit tests for src/config.py — env var loading with defaults."""

import importlib
import os


def test_default_port(monkeypatch):
    monkeypatch.delenv("MCP_SUMMARIZER_PORT", raising=False)
    import src.config as cfg
    importlib.reload(cfg)
    assert cfg.MCP_SUMMARIZER_PORT == 8007


def test_custom_port(monkeypatch):
    monkeypatch.setenv("MCP_SUMMARIZER_PORT", "9999")
    import src.config as cfg
    importlib.reload(cfg)
    assert cfg.MCP_SUMMARIZER_PORT == 9999


def test_default_llm_model(monkeypatch):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    import src.config as cfg
    importlib.reload(cfg)
    assert cfg.LLM_MODEL == "openrouter:openai/gpt-4o-mini"


def test_custom_llm_model(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "google/gemini-2.0-flash")
    import src.config as cfg
    importlib.reload(cfg)
    assert cfg.LLM_MODEL == "google/gemini-2.0-flash"


def test_default_chunk_size(monkeypatch):
    monkeypatch.delenv("DEFAULT_CHUNK_SIZE_TOKENS", raising=False)
    import src.config as cfg
    importlib.reload(cfg)
    assert cfg.DEFAULT_CHUNK_SIZE_TOKENS == 8000


def test_custom_chunk_size(monkeypatch):
    monkeypatch.setenv("DEFAULT_CHUNK_SIZE_TOKENS", "4000")
    import src.config as cfg
    importlib.reload(cfg)
    assert cfg.DEFAULT_CHUNK_SIZE_TOKENS == 4000


def test_default_chunk_overlap(monkeypatch):
    monkeypatch.delenv("DEFAULT_CHUNK_OVERLAP_TOKENS", raising=False)
    import src.config as cfg
    importlib.reload(cfg)
    assert cfg.DEFAULT_CHUNK_OVERLAP_TOKENS == 500


def test_default_max_output_tokens(monkeypatch):
    monkeypatch.delenv("DEFAULT_MAX_OUTPUT_TOKENS", raising=False)
    import src.config as cfg
    importlib.reload(cfg)
    assert cfg.DEFAULT_MAX_OUTPUT_TOKENS == 5000


def test_custom_max_output_tokens(monkeypatch):
    monkeypatch.setenv("DEFAULT_MAX_OUTPUT_TOKENS", "10000")
    import src.config as cfg
    importlib.reload(cfg)
    assert cfg.DEFAULT_MAX_OUTPUT_TOKENS == 10000
