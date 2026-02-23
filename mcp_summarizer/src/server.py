"""MCP Summarizer Service — FastMCP server with summarization tools."""

import logging

from mcp.server.fastmcp import FastMCP
from shared.prompt_loader import load_prompt
from src.config import DEFAULT_MAX_OUTPUT_TOKENS, MCP_SUMMARIZER_PORT
from src.logging_config import setup_logging
from src.summarizer import map_reduce_summarize
from src.tokens import count_tokens

setup_logging()
logger = logging.getLogger(__name__)

server = FastMCP(name="Summarizer Service", host="0.0.0.0", port=MCP_SUMMARIZER_PORT)

# Load prompt templates once at import
_chunk_template = load_prompt(__file__, "summarize_chunk")
_extraction_template = load_prompt(__file__, "summarize_chunk_extraction")
_merge_template = load_prompt(__file__, "merge_summaries")


@server.tool()
async def summarize(
    content: str,
    max_output_tokens: int = 0,
    focus_areas: str = "",
    strategy: str = "semantic",
) -> str:
    """Summarize large text content using map-reduce chunking.

    Args:
        content: The text to summarize.
        max_output_tokens: Target summary size in tokens. 0 = use service default.
        focus_areas: Comma-separated topics to emphasize (e.g., "NPCs, factions, lore").
                     Empty = general summarization.
        strategy: Chunking strategy — "semantic" (default) or "token".

    Returns:
        A compressed summary string.
    """
    try:
        target = max_output_tokens if max_output_tokens > 0 else DEFAULT_MAX_OUTPUT_TOKENS

        # Bypass: already small enough
        if count_tokens(content) <= target:
            return content

        focus_instructions = f"\nFocus especially on: {focus_areas}\n" if focus_areas else ""
        return await map_reduce_summarize(
            content=content,
            prompt_template=_chunk_template,
            merge_template=_merge_template,
            max_output_tokens=target,
            strategy=strategy,
            focus_instructions=focus_instructions,
        )
    except Exception:
        logger.warning("summarize_failed_returning_original", exc_info=True)
        return content


@server.tool()
async def summarize_for_extraction(
    content: str,
    schema_hint: str,
    max_output_tokens: int = 0,
) -> str:
    """Summarize content optimized for downstream structured extraction.

    Args:
        content: The text to summarize.
        schema_hint: Description of target extraction schema. Tells the summarizer
                     what categories of information to preserve (e.g., "zone metadata,
                     NPCs with faction allegiances, faction hierarchy, lore events").
        max_output_tokens: Target summary size in tokens. 0 = use service default.

    Returns:
        A summary optimized for extraction — preserves named entities, relationships,
        and structured details while discarding boilerplate.
    """
    try:
        target = max_output_tokens if max_output_tokens > 0 else DEFAULT_MAX_OUTPUT_TOKENS

        # Bypass: already small enough
        if count_tokens(content) <= target:
            return content

        return await map_reduce_summarize(
            content=content,
            prompt_template=_extraction_template,
            merge_template=_merge_template,
            max_output_tokens=target,
            strategy="semantic",
            schema_hint=schema_hint,
            focus_instructions=f"\nFocus especially on: {schema_hint}\n",
        )
    except Exception:
        logger.warning("summarize_for_extraction_failed_returning_original", exc_info=True)
        return content


if __name__ == "__main__":
    server.run(transport="streamable-http")
