"""Unit tests for src/server.py — MCP tool endpoints."""

from unittest.mock import AsyncMock, patch

import pytest


# --- summarize tool ---


@pytest.mark.asyncio
async def test_summarize_bypass_small_content():
    """Content below target should be returned unchanged without calling LLM."""
    from src.server import summarize

    result = await summarize(content="Short text.", max_output_tokens=5000)
    assert result == "Short text."


@pytest.mark.asyncio
async def test_summarize_bypass_default_target():
    """Bypass should work with default max_output_tokens (0 → service default)."""
    from src.server import summarize

    result = await summarize(content="Short text.")
    assert result == "Short text."


@pytest.mark.asyncio
async def test_summarize_calls_map_reduce():
    """Large content should trigger map_reduce_summarize."""
    from src.server import summarize

    large_content = "word " * 10000
    with patch("src.server.map_reduce_summarize", new_callable=AsyncMock) as mock_mr:
        mock_mr.return_value = "Summarized content."
        result = await summarize(
            content=large_content,
            max_output_tokens=100,
            focus_areas="NPCs, factions",
            strategy="token",
        )

    assert result == "Summarized content."
    call_kwargs = mock_mr.call_args[1]
    assert call_kwargs["max_output_tokens"] == 100
    assert call_kwargs["strategy"] == "token"
    assert "NPCs, factions" in call_kwargs["focus_instructions"]


@pytest.mark.asyncio
async def test_summarize_empty_focus_areas():
    """Empty focus_areas should produce empty focus_instructions."""
    from src.server import summarize

    large_content = "word " * 10000
    with patch("src.server.map_reduce_summarize", new_callable=AsyncMock) as mock_mr:
        mock_mr.return_value = "Summary."
        await summarize(content=large_content, max_output_tokens=100, focus_areas="")

    call_kwargs = mock_mr.call_args[1]
    assert call_kwargs["focus_instructions"] == ""


@pytest.mark.asyncio
async def test_summarize_graceful_degradation():
    """On exception, should return original content."""
    from src.server import summarize

    large_content = "word " * 10000
    with patch("src.server.map_reduce_summarize", new_callable=AsyncMock) as mock_mr:
        mock_mr.side_effect = Exception("LLM error")
        result = await summarize(content=large_content, max_output_tokens=100)

    assert result == large_content


@pytest.mark.asyncio
async def test_summarize_uses_correct_template():
    """summarize should use the chunk template (not extraction)."""
    from src.server import _chunk_template, summarize

    large_content = "word " * 10000
    with patch("src.server.map_reduce_summarize", new_callable=AsyncMock) as mock_mr:
        mock_mr.return_value = "Summary."
        await summarize(content=large_content, max_output_tokens=100)

    call_kwargs = mock_mr.call_args[1]
    assert call_kwargs["prompt_template"] == _chunk_template


# --- summarize_for_extraction tool ---


@pytest.mark.asyncio
async def test_extraction_bypass_small_content():
    """Content below target should be returned unchanged."""
    from src.server import summarize_for_extraction

    result = await summarize_for_extraction(
        content="Short text.",
        schema_hint="zone data",
        max_output_tokens=5000,
    )
    assert result == "Short text."


@pytest.mark.asyncio
async def test_extraction_calls_map_reduce():
    """Large content should trigger map_reduce_summarize with extraction template."""
    from src.server import _extraction_template, summarize_for_extraction

    large_content = "word " * 10000
    with patch("src.server.map_reduce_summarize", new_callable=AsyncMock) as mock_mr:
        mock_mr.return_value = "Extraction summary."
        result = await summarize_for_extraction(
            content=large_content,
            schema_hint="zone metadata, NPCs, factions",
            max_output_tokens=200,
        )

    assert result == "Extraction summary."
    call_kwargs = mock_mr.call_args[1]
    assert call_kwargs["prompt_template"] == _extraction_template
    assert call_kwargs["max_output_tokens"] == 200
    assert call_kwargs["strategy"] == "semantic"
    assert call_kwargs["schema_hint"] == "zone metadata, NPCs, factions"
    assert "zone metadata, NPCs, factions" in call_kwargs["focus_instructions"]


@pytest.mark.asyncio
async def test_extraction_graceful_degradation():
    """On exception, should return original content."""
    from src.server import summarize_for_extraction

    large_content = "word " * 10000
    with patch("src.server.map_reduce_summarize", new_callable=AsyncMock) as mock_mr:
        mock_mr.side_effect = RuntimeError("Service down")
        result = await summarize_for_extraction(
            content=large_content,
            schema_hint="zone data",
            max_output_tokens=100,
        )

    assert result == large_content


@pytest.mark.asyncio
async def test_extraction_always_uses_semantic_strategy():
    """summarize_for_extraction should always use semantic strategy."""
    from src.server import summarize_for_extraction

    large_content = "word " * 10000
    with patch("src.server.map_reduce_summarize", new_callable=AsyncMock) as mock_mr:
        mock_mr.return_value = "Summary."
        await summarize_for_extraction(
            content=large_content,
            schema_hint="items",
            max_output_tokens=100,
        )

    call_kwargs = mock_mr.call_args[1]
    assert call_kwargs["strategy"] == "semantic"


@pytest.mark.asyncio
async def test_extraction_default_max_output_tokens():
    """When max_output_tokens=0, should use service default."""
    from src.config import DEFAULT_MAX_OUTPUT_TOKENS
    from src.server import summarize_for_extraction

    large_content = "word " * 10000
    with patch("src.server.map_reduce_summarize", new_callable=AsyncMock) as mock_mr:
        mock_mr.return_value = "Summary."
        await summarize_for_extraction(
            content=large_content,
            schema_hint="data",
        )

    call_kwargs = mock_mr.call_args[1]
    assert call_kwargs["max_output_tokens"] == DEFAULT_MAX_OUTPUT_TOKENS


# --- Template loading ---


def test_templates_loaded():
    """Prompt templates should be loaded at import time."""
    from src.server import _chunk_template, _extraction_template, _merge_template

    assert "Summarize the following content" in _chunk_template
    assert "structured data extraction" in _extraction_template
    assert "Merge them into a single coherent summary" in _merge_template
