"""Unit tests for src/summarizer.py — map-reduce summarization with mocked LLM."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tenacity import RetryError

from src.summarizer import (
    MAX_CONCURRENT_LLM_CALLS,
    MAX_REDUCE_PASSES,
    _llm_call,
    _summarize_chunk,
    map_reduce_summarize,
)
from src.tokens import count_tokens


# --- Helpers ---


def _make_mock_result(output: str):
    """Create a mock pydantic-ai RunResult object."""
    result = MagicMock()
    result.output = output
    return result


# --- _llm_call ---


@pytest.mark.asyncio
async def test_llm_call_returns_content():
    mock_result = _make_mock_result("Summary text.")
    with patch("src.summarizer._agent") as mock_agent:
        mock_agent.run = AsyncMock(return_value=mock_result)
        result = await _llm_call("Summarize this.", max_tokens=500)
    assert result == "Summary text."


@pytest.mark.asyncio
async def test_llm_call_passes_correct_params():
    mock_result = _make_mock_result("OK")
    with patch("src.summarizer._agent") as mock_agent:
        mock_agent.run = AsyncMock(return_value=mock_result)
        await _llm_call("test prompt", max_tokens=1000)
        call_args = mock_agent.run.call_args
        assert call_args[0][0] == "test prompt"
        model_settings = call_args[1]["model_settings"]
        assert model_settings["max_tokens"] == 1000
        assert model_settings["temperature"] == 0.1


@pytest.mark.asyncio
async def test_llm_call_retries_on_failure():
    mock_result = _make_mock_result("Got it.")
    with patch("src.summarizer._agent") as mock_agent:
        mock_agent.run = AsyncMock(
            side_effect=[Exception("API error"), Exception("API error"), mock_result]
        )
        with patch("src.summarizer._llm_call.retry.wait", return_value=0):
            result = await _llm_call("Summarize this.", max_tokens=500)
    assert result == "Got it."
    assert mock_agent.run.call_count == 3


@pytest.mark.asyncio
async def test_llm_call_raises_after_max_retries():
    with patch("src.summarizer._agent") as mock_agent:
        mock_agent.run = AsyncMock(
            side_effect=Exception("Persistent failure")
        )
        with patch("src.summarizer._llm_call.retry.wait", return_value=0):
            with pytest.raises(RetryError):
                await _llm_call("Summarize this.", max_tokens=500)
    assert mock_agent.run.call_count == 3


# --- _summarize_chunk ---


@pytest.mark.asyncio
async def test_summarize_chunk_formats_prompt():
    template = "Summarize: {content}\nFocus: {focus_instructions}"
    with patch("src.summarizer._llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Chunk summary."
        result = await _summarize_chunk(
            "Some text.",
            template,
            max_tokens_per_chunk=500,
            focus_instructions="NPCs and factions",
        )
    assert result == "Chunk summary."
    call_args = mock_llm.call_args
    prompt = call_args[0][0]
    assert "Some text." in prompt
    assert "NPCs and factions" in prompt


@pytest.mark.asyncio
async def test_summarize_chunk_passes_max_tokens():
    template = "{content}"
    with patch("src.summarizer._llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Summary."
        await _summarize_chunk("text", template, max_tokens_per_chunk=1234)
    assert mock_llm.call_args[0][1] == 1234


# --- map_reduce_summarize ---


@pytest.mark.asyncio
async def test_bypass_small_content():
    """Content already under target size should be returned unchanged."""
    small = "Short text."
    result = await map_reduce_summarize(
        content=small,
        prompt_template="{content}",
        merge_template="{content}",
        max_output_tokens=5000,
    )
    assert result == small


@pytest.mark.asyncio
async def test_map_phase_chunks_and_summarizes():
    """Large content should be chunked and each chunk summarized."""
    large_content = "word " * 500  # Well over any small threshold
    prompt_template = "{content}{focus_instructions}"
    merge_template = "{content}{focus_instructions}"

    with patch("src.summarizer._llm_call", new_callable=AsyncMock) as mock_llm:
        # Return small summaries so reduce phase isn't triggered
        mock_llm.return_value = "chunk summary"
        result = await map_reduce_summarize(
            content=large_content,
            prompt_template=prompt_template,
            merge_template=merge_template,
            max_output_tokens=100,
            strategy="token",
            chunk_size=100,
            chunk_overlap=0,
            focus_instructions="",
        )

    # LLM should have been called for each chunk
    assert mock_llm.call_count >= 2
    assert "chunk summary" in result


@pytest.mark.asyncio
async def test_reduce_phase_merges_when_over_target():
    """When map summaries combined exceed target, reduce should merge them."""
    large_content = "word " * 500
    prompt_template = "{content}{focus_instructions}"
    merge_template = "Merge: {content} max_tokens={max_tokens}{focus_instructions}"

    call_count = 0

    async def mock_llm_fn(prompt, max_tokens):
        nonlocal call_count
        call_count += 1
        # Map phase: return summaries that are too large combined
        if "Merge:" not in prompt:
            return "This is a chunk summary with enough words to be substantial. " * 3
        # Reduce phase: return a small enough result
        return "Final merged summary."

    with patch("src.summarizer._llm_call", side_effect=mock_llm_fn):
        result = await map_reduce_summarize(
            content=large_content,
            prompt_template=prompt_template,
            merge_template=merge_template,
            max_output_tokens=50,
            strategy="token",
            chunk_size=100,
            chunk_overlap=0,
            focus_instructions="",
        )

    assert result == "Final merged summary."
    # Should have map calls + at least one reduce call
    assert call_count >= 3


@pytest.mark.asyncio
async def test_reduce_phase_max_passes():
    """Reduce phase should not exceed MAX_REDUCE_PASSES even if still over target."""
    large_content = "word " * 500
    prompt_template = "{content}{focus_instructions}"
    merge_template = "Merge: {content} max_tokens={max_tokens}{focus_instructions}"

    reduce_calls = 0

    async def mock_llm_fn(prompt, max_tokens):
        nonlocal reduce_calls
        if "Merge:" in prompt:
            reduce_calls += 1
            # Always return content that's still over target
            return "Still too large. " * 50
        return "Chunk summary content."

    with patch("src.summarizer._llm_call", side_effect=mock_llm_fn):
        await map_reduce_summarize(
            content=large_content,
            prompt_template=prompt_template,
            merge_template=merge_template,
            max_output_tokens=10,
            strategy="token",
            chunk_size=100,
            chunk_overlap=0,
            focus_instructions="",
        )

    assert reduce_calls <= MAX_REDUCE_PASSES


@pytest.mark.asyncio
async def test_semaphore_limits_concurrency():
    """Concurrent LLM calls should be bounded by the semaphore."""
    large_content = "word " * 2000  # Enough for many chunks
    prompt_template = "{content}{focus_instructions}"
    merge_template = "{content}{focus_instructions}"

    peak_concurrent = 0
    current_concurrent = 0
    lock = asyncio.Lock()

    async def mock_llm_fn(prompt, max_tokens):
        nonlocal peak_concurrent, current_concurrent
        async with lock:
            current_concurrent += 1
            if current_concurrent > peak_concurrent:
                peak_concurrent = current_concurrent
        await asyncio.sleep(0.01)  # Simulate brief work
        async with lock:
            current_concurrent -= 1
        return "summary"

    with patch("src.summarizer._llm_call", side_effect=mock_llm_fn):
        await map_reduce_summarize(
            content=large_content,
            prompt_template=prompt_template,
            merge_template=merge_template,
            max_output_tokens=50,
            strategy="token",
            chunk_size=50,
            chunk_overlap=0,
            focus_instructions="",
        )

    assert peak_concurrent <= MAX_CONCURRENT_LLM_CALLS


@pytest.mark.asyncio
async def test_failure_propagates():
    """If LLM persistently fails, the error should propagate up."""
    large_content = "word " * 500
    prompt_template = "{content}{focus_instructions}"
    merge_template = "{content}{focus_instructions}"

    with patch("src.summarizer._llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = Exception("LLM down")
        with pytest.raises(Exception, match="LLM down"):
            await map_reduce_summarize(
                content=large_content,
                prompt_template=prompt_template,
                merge_template=merge_template,
                max_output_tokens=50,
                strategy="token",
                chunk_size=100,
                chunk_overlap=0,
                focus_instructions="",
            )


@pytest.mark.asyncio
async def test_logging_map_phase(caplog):
    """Map phase should emit a log with chunk info."""
    large_content = "word " * 500
    prompt_template = "{content}{focus_instructions}"
    merge_template = "{content}{focus_instructions}"

    with patch("src.summarizer._llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "summary"
        import logging
        with caplog.at_level(logging.INFO, logger="src.summarizer"):
            await map_reduce_summarize(
                content=large_content,
                prompt_template=prompt_template,
                merge_template=merge_template,
                max_output_tokens=100,
                strategy="token",
                chunk_size=100,
                chunk_overlap=0,
                focus_instructions="",
            )

    assert any("map_phase_started" in r.message for r in caplog.records)
    assert any("summarization_complete" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_compression_ratio_logged(caplog):
    """Completion log should include compression ratio."""
    large_content = "word " * 500
    prompt_template = "{content}{focus_instructions}"
    merge_template = "{content}{focus_instructions}"

    with patch("src.summarizer._llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "brief"
        import logging
        with caplog.at_level(logging.INFO, logger="src.summarizer"):
            await map_reduce_summarize(
                content=large_content,
                prompt_template=prompt_template,
                merge_template=merge_template,
                max_output_tokens=100,
                strategy="token",
                chunk_size=100,
                chunk_overlap=0,
                focus_instructions="",
            )

    complete_records = [r for r in caplog.records if r.message == "summarization_complete"]
    assert len(complete_records) == 1
    assert hasattr(complete_records[0], "compression_ratio")
    assert complete_records[0].compression_ratio > 0
