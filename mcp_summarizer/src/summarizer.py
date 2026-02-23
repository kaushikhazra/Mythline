"""Map-reduce summarization engine with LLM calls."""

import asyncio
import logging

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings
from tenacity import retry, stop_after_attempt, wait_exponential

from src.chunker import chunk_content
from src.config import (
    DEFAULT_CHUNK_OVERLAP_TOKENS,
    DEFAULT_CHUNK_SIZE_TOKENS,
    LLM_MODEL,
)
from src.tokens import count_tokens

logger = logging.getLogger(__name__)

_agent = Agent(LLM_MODEL, output_type=str)

MAX_REDUCE_PASSES = 3
MAX_CONCURRENT_LLM_CALLS = 5
_llm_semaphore = asyncio.Semaphore(MAX_CONCURRENT_LLM_CALLS)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
async def _llm_call(prompt: str, max_tokens: int) -> str:
    """Call the LLM with retry. Raises on persistent failure."""
    result = await _agent.run(
        prompt,
        model_settings=ModelSettings(max_tokens=max_tokens, temperature=0.1),
    )
    return result.output


async def _summarize_chunk(
    chunk: str,
    prompt_template: str,
    max_tokens_per_chunk: int,
    **format_kwargs,
) -> str:
    """Summarize a single chunk using the given prompt template."""
    prompt = prompt_template.format(content=chunk, **format_kwargs)
    return await _llm_call(prompt, max_tokens_per_chunk)


async def map_reduce_summarize(
    content: str,
    prompt_template: str,
    merge_template: str,
    max_output_tokens: int,
    strategy: str = "semantic",
    chunk_size: int = DEFAULT_CHUNK_SIZE_TOKENS,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP_TOKENS,
    **format_kwargs,
) -> str:
    """Full map-reduce summarization pipeline.

    1. Chunk content into manageable segments.
    2. Map: summarize each chunk independently (concurrent).
    3. Reduce: if combined summaries exceed target, merge and repeat.
    """
    input_tokens = count_tokens(content)

    # Bypass: already small enough
    if input_tokens <= max_output_tokens:
        return content

    # --- Map Phase ---
    chunks = chunk_content(content, strategy, chunk_size, chunk_overlap)
    max_tokens_per_chunk = max(max_output_tokens // len(chunks), 500)

    logger.info(
        "map_phase_started",
        extra={
            "input_tokens": input_tokens,
            "num_chunks": len(chunks),
            "strategy": strategy,
            "max_tokens_per_chunk": max_tokens_per_chunk,
            "model": LLM_MODEL,
        },
    )

    # Concurrent chunk summarization (bounded by semaphore)
    async def _bounded_summarize(chunk: str) -> str:
        async with _llm_semaphore:
            return await _summarize_chunk(
                chunk, prompt_template, max_tokens_per_chunk, **format_kwargs
            )

    tasks = [_bounded_summarize(chunk) for chunk in chunks]
    summaries = await asyncio.gather(*tasks)

    # --- Reduce Phase ---
    combined = "\n\n---\n\n".join(summaries)
    combined_tokens = count_tokens(combined)

    for pass_num in range(MAX_REDUCE_PASSES):
        if combined_tokens <= max_output_tokens:
            break

        logger.info(
            "reduce_pass",
            extra={
                "pass": pass_num + 1,
                "combined_tokens": combined_tokens,
                "target": max_output_tokens,
                "model": LLM_MODEL,
            },
        )

        merge_prompt = merge_template.format(
            content=combined,
            max_tokens=max_output_tokens,
            **format_kwargs,
        )
        combined = await _llm_call(merge_prompt, max_output_tokens)
        combined_tokens = count_tokens(combined)

    output_tokens = count_tokens(combined)
    ratio = input_tokens / max(output_tokens, 1)
    logger.info(
        "summarization_complete",
        extra={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "compression_ratio": round(ratio, 1),
            "num_chunks": len(chunks),
            "strategy": strategy,
            "model": LLM_MODEL,
        },
    )

    return combined
