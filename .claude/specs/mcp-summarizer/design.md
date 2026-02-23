# MCP Summarizer Service — Design

## Decisions Log

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Two separate tools (`summarize`, `summarize_for_extraction`) rather than one overloaded tool with a mode flag | Each has a distinct prompt strategy — general vs. extraction-aware. Cleaner interface, easier to document. (MS-1, MS-2) |
| D2 | Parameters use simple types (str, int). `focus_areas` is comma-separated string, not list | Consistent with existing MCP tools (search, storage) which all use simple parameter types. (MS-1) |
| D3 | Return type is `str` for both tools | Callers (pipeline, agents) consume a string. No need for structured response objects for summarized text. (MS-1, MS-2) |
| D4 | Token counting via `tiktoken` (cl100k_base encoding) | Accurate for GPT-4o family (our default). Approximate but sufficient for chunking heuristics on other models. (MS-3) |
| D5 | Bypass logic — return content unchanged if below target size | No unnecessary LLM calls. Saves tokens and latency for small content. (MS-1) |
| D6 | Use `openai` SDK directly (not pydantic-ai) for LLM calls | Summarizer makes simple prompt-to-response calls with no tools or structured output. OpenRouter is OpenAI-compatible. pydantic-ai adds unnecessary complexity for a stateless MCP service. (MS-4) |
| D7 | Build context from repo root (like mcp_storage) to include `shared/` | Prompts use `shared.prompt_loader.load_prompt()`. Structural rule: no hardcoded prompts in Python. (MS-1, MS-2) |
| D8 | Summarize per-step in the pipeline (not all-at-once before extraction) | Each step's content is focused on one topic. Summarizing per-step with the topic as schema_hint produces better domain-aware compression than a monolithic summarization of all content. (MS-5) |
| D9 | Concurrency limiter (semaphore) on concurrent LLM calls | Prevents overwhelming OpenRouter API with burst requests when chunk count is high (~25 chunks). Max 5 concurrent. (MS-6) |
| D10 | Summarizer NOT added to researcher's mcp_config.json | mcp_config.json feeds the pydantic-ai agent toolset. The summarizer is called by the pipeline via `mcp_call()`, not by the agent. Storage MCP follows the same pattern (called via `mcp_call`, not in mcp_config.json). (MS-5) |
| D11 | Dedicated `logging_config.py` with JSON formatter and `service_id` | All log events include `service_id: "mcp_summarizer"` for filtering in aggregated log streams. Log extras include the LLM model name for debugging quality changes across model switches. (MS-6) |

---

## 1. MCP Tool Interface

### `summarize` Tool

General-purpose map-reduce summarization.

```python
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
```

### `summarize_for_extraction` Tool

Extraction-targeted summarization — preserves structured details matching a schema.

```python
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
```

### Bypass Logic

Both tools check input size before processing:

```python
input_tokens = count_tokens(content)
target = max_output_tokens if max_output_tokens > 0 else DEFAULT_MAX_OUTPUT_TOKENS

if input_tokens <= target:
    return content  # Already small enough — no compression needed
```

---

## 2. Chunking Engine

Module: `src/chunker.py`

### 2.1 Semantic Boundary Chunking (default)

Splits markdown content at structural boundaries — headers, horizontal rules, and paragraph breaks — then accumulates sections into chunks of approximately `chunk_size_tokens`.

```python
import re
from src.tokens import count_tokens

# Primary boundaries: markdown headers and horizontal rules
HEADER_PATTERN = re.compile(r"(?=^#{1,4}\s|\n-{3,}\n)", re.MULTILINE)


def _split_by_paragraphs(text: str) -> list[str]:
    """Split text at paragraph breaks (double newlines).

    Secondary boundary — used when a header-delimited section exceeds
    chunk_size but has natural paragraph breaks within it.
    """
    parts = re.split(r"\n\n+", text)
    return [p.strip() for p in parts if p.strip()]


def chunk_semantic(
    content: str,
    chunk_size: int,
    overlap: int,
) -> list[str]:
    """Split content at markdown structural boundaries.

    Algorithm:
    1. Split content by headers and horizontal rules (primary boundaries).
    2. Track the header stack (most recent header at each level).
    3. Accumulate units into chunks until approaching chunk_size.
    4. If a single unit exceeds chunk_size, try splitting at paragraph
       breaks (secondary boundaries) before falling back to token-based.
    5. Prepend active header context to each chunk for continuity.
    """
    sections = HEADER_PATTERN.split(content)
    sections = [s.strip() for s in sections if s.strip()]

    if not sections:
        return [content] if content.strip() else []

    chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens = 0
    header_context = ""  # Most recent top-level header

    for section in sections:
        section_tokens = count_tokens(section)

        # Track header context for propagation
        header_match = re.match(r"^(#{1,2}\s+.+)", section)
        if header_match:
            header_context = header_match.group(1)

        if section_tokens > chunk_size:
            # Oversized section — finalize current chunk
            if current_parts:
                chunks.append("\n\n".join(current_parts))
                current_parts = []
                current_tokens = 0

            # Try paragraph-level splitting first (secondary boundary)
            paragraphs = _split_by_paragraphs(section)
            if len(paragraphs) > 1:
                # Re-accumulate paragraphs into sub-chunks
                sub_parts: list[str] = []
                sub_tokens = 0
                if header_context:
                    sub_parts.append(header_context)
                    sub_tokens = count_tokens(header_context)
                for para in paragraphs:
                    para_tokens = count_tokens(para)
                    if para_tokens > chunk_size:
                        # Single paragraph too large — token-split it
                        if sub_parts:
                            chunks.append("\n\n".join(sub_parts))
                            sub_parts = []
                            sub_tokens = 0
                        chunks.extend(chunk_token_based(para, chunk_size, overlap))
                    elif sub_tokens + para_tokens > chunk_size and sub_parts:
                        chunks.append("\n\n".join(sub_parts))
                        sub_parts = [header_context] if header_context else []
                        sub_tokens = count_tokens(header_context) if header_context else 0
                        sub_parts.append(para)
                        sub_tokens += para_tokens
                    else:
                        sub_parts.append(para)
                        sub_tokens += para_tokens
                if sub_parts:
                    chunks.append("\n\n".join(sub_parts))
            else:
                # No paragraph breaks — fall back to token-based split
                sub_chunks = chunk_token_based(section, chunk_size, overlap)
                if header_context and sub_chunks:
                    sub_chunks[0] = header_context + "\n\n" + sub_chunks[0]
                chunks.extend(sub_chunks)
            continue

        if current_tokens + section_tokens > chunk_size and current_parts:
            # Would exceed limit — finalize current chunk
            chunks.append("\n\n".join(current_parts))
            current_parts = []
            current_tokens = 0
            # Propagate header context to new chunk
            if header_context:
                current_parts.append(header_context)
                current_tokens = count_tokens(header_context)

        current_parts.append(section)
        current_tokens += section_tokens

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return chunks
```

### 2.2 Token-Based Chunking (fallback)

Fixed token boundaries with overlap. Used as fallback for unstructured content or oversized sections.

```python
from src.tokens import encode, decode


def chunk_token_based(
    content: str,
    chunk_size: int,
    overlap: int,
) -> list[str]:
    """Split content at fixed token boundaries with overlap."""
    tokens = encode(content)

    if len(tokens) <= chunk_size:
        return [content]

    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunks.append(decode(tokens[start:end]))
        if end >= len(tokens):
            break
        start = end - overlap

    return chunks
```

### 2.3 Strategy Dispatcher

```python
def chunk_content(
    content: str,
    strategy: str = "semantic",
    chunk_size: int = DEFAULT_CHUNK_SIZE_TOKENS,
    overlap: int = DEFAULT_CHUNK_OVERLAP_TOKENS,
) -> list[str]:
    """Chunk content using the specified strategy."""
    if strategy == "token":
        return chunk_token_based(content, chunk_size, overlap)
    return chunk_semantic(content, chunk_size, overlap)
```

---

## 3. Map-Reduce Summarization Engine

Module: `src/summarizer.py`

### 3.1 LLM Client Setup

```python
from openai import AsyncOpenAI
from src.config import OPENROUTER_API_KEY, LLM_MODEL, OPENROUTER_BASE_URL, DEFAULT_CHUNK_SIZE_TOKENS, DEFAULT_CHUNK_OVERLAP_TOKENS

client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
)
```

### 3.2 Per-Chunk Summarization (Map Phase)

```python
from shared.prompt_loader import load_prompt
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
async def _llm_call(prompt: str, max_tokens: int) -> str:
    """Call the LLM with retry. Raises on persistent failure."""
    response = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.1,  # Low temperature for faithful summarization
    )
    return response.choices[0].message.content or ""


async def _summarize_chunk(
    chunk: str,
    prompt_template: str,
    max_tokens_per_chunk: int,
    **format_kwargs,
) -> str:
    """Summarize a single chunk using the given prompt template."""
    prompt = prompt_template.format(content=chunk, **format_kwargs)
    return await _llm_call(prompt, max_tokens_per_chunk)
```

### 3.3 Map-Reduce Orchestration

```python
import asyncio
import logging
from src.chunker import chunk_content
from src.tokens import count_tokens

logger = logging.getLogger(__name__)
MAX_REDUCE_PASSES = 3
MAX_CONCURRENT_LLM_CALLS = 5
_llm_semaphore = asyncio.Semaphore(MAX_CONCURRENT_LLM_CALLS)


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
```

---

## 4. Prompt Templates

All prompts live in `mcp_summarizer/prompts/`. Loaded via `shared.prompt_loader.load_prompt(__file__, name)`.

### `prompts/summarize_chunk.md`

General-purpose chunk summarization.

```markdown
Summarize the following content concisely. Preserve key facts, names, relationships, and specific details. Remove boilerplate, navigation text, repetitive content, and site chrome.
{focus_instructions}
Content:

{content}
```

Where `{focus_instructions}` is either empty (no focus areas) or:
```
Focus especially on: {focus_areas}
```

### `prompts/summarize_chunk_extraction.md`

Extraction-aware chunk summarization.

```markdown
Summarize the following content for downstream structured data extraction.

Target extraction schema: {schema_hint}

Preserve ALL details that match the schema — names, relationships, numbers, dates, hierarchies, allegiances. Keep specific data points even if they seem minor.

Aggressively discard: navigation menus, cookie notices, advertisements, site chrome, content unrelated to the schema, and repetitive boilerplate.

Content:

{content}
```

### `prompts/merge_summaries.md`

Merge multiple chunk summaries into a single coherent summary.

```markdown
The following are summaries of different sections of a larger document. Merge them into a single coherent summary of no more than {max_tokens} tokens.

Eliminate redundancy across sections. Preserve all unique facts, names, and relationships. Maintain a logical flow.
{focus_instructions}
Summaries:

{content}
```

---

## 5. Service Structure

```
mcp_summarizer/
├── Dockerfile
├── .env.example
├── pyproject.toml
├── conftest.py
├── prompts/
│   ├── summarize_chunk.md
│   ├── summarize_chunk_extraction.md
│   └── merge_summaries.md
├── src/
│   ├── __init__.py
│   ├── server.py            # FastMCP server + tool definitions
│   ├── config.py             # Env var loading
│   ├── logging_config.py     # Structured JSON logging with service_id
│   ├── chunker.py            # Chunking engine (semantic + token-based)
│   ├── summarizer.py         # Map-reduce orchestration + LLM calls
│   └── tokens.py             # Token counting (tiktoken wrapper)
└── tests/
    ├── __init__.py
    ├── test_chunker.py
    ├── test_summarizer.py
    ├── test_tokens.py
    └── test_server.py
```

### `src/config.py`

```python
import os

MCP_SUMMARIZER_PORT = int(os.getenv("MCP_SUMMARIZER_PORT", "8007"))
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_CHUNK_SIZE_TOKENS = int(os.getenv("DEFAULT_CHUNK_SIZE_TOKENS", "8000"))
DEFAULT_CHUNK_OVERLAP_TOKENS = int(os.getenv("DEFAULT_CHUNK_OVERLAP_TOKENS", "500"))
DEFAULT_MAX_OUTPUT_TOKENS = int(os.getenv("DEFAULT_MAX_OUTPUT_TOKENS", "5000"))
```

### `src/tokens.py`

```python
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
```

### `src/logging_config.py`

Structured JSON logging with `service_id` in every event.

```python
import logging
import json
import sys

SERVICE_ID = "mcp_summarizer"


class JsonFormatter(logging.Formatter):
    """JSON log formatter that includes service_id in every event."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname.lower(),
            "service_id": SERVICE_ID,
            "event": record.getMessage(),
            "logger": record.name,
        }
        # Merge structured extras (from extra={...} in log calls)
        for key in ("input_tokens", "output_tokens", "compression_ratio",
                     "num_chunks", "strategy", "max_tokens_per_chunk",
                     "combined_tokens", "target", "pass", "topic",
                     "raw_blocks", "raw_chars", "summary_chars", "model"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = str(record.exc_info[1])
        return json.dumps(log_entry)


def setup_logging() -> None:
    """Configure structured JSON logging for the summarizer service."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
```

### `src/server.py`

```python
import logging

from mcp.server.fastmcp import FastMCP
from shared.prompt_loader import load_prompt
from src.config import MCP_SUMMARIZER_PORT, DEFAULT_MAX_OUTPUT_TOKENS
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
        return content  # Graceful degradation: return original content


@server.tool()
async def summarize_for_extraction(
    content: str,
    schema_hint: str,
    max_output_tokens: int = 0,
) -> str:
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
            strategy="semantic",  # Always semantic for extraction
            schema_hint=schema_hint,
            focus_instructions=f"\nFocus especially on: {schema_hint}\n",
        )
    except Exception:
        logger.warning("summarize_for_extraction_failed_returning_original", exc_info=True)
        return content  # Graceful degradation: return original content


if __name__ == "__main__":
    server.run(transport="streamable-http")
```

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY mcp_summarizer/pyproject.toml .
RUN uv pip install --system --no-cache .

# Pre-download tiktoken encoding data to avoid cold-start delay on first request
RUN python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

COPY shared/ shared/
COPY mcp_summarizer/prompts/ prompts/
COPY mcp_summarizer/src/ src/

EXPOSE 8007

CMD ["python", "-m", "src.server"]
```

### `pyproject.toml`

```toml
[project]
name = "mcp-summarizer"
version = "0.1.0"
description = "Content summarization MCP service — map-reduce chunking with domain-aware LLM compression"
requires-python = ">=3.12"
dependencies = [
    "mcp>=1.26.0",
    "uvicorn>=0.34.0",
    "openai>=1.60.0",
    "tiktoken>=0.9.0",
    "tenacity>=9.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=1.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

---

## 6. Pipeline Integration

### Changes to `_make_research_step` in `a_world_lore_researcher/src/pipeline.py`

Add a summarization call between `research_zone()` and `_accumulate_research()`:

```python
from src.config import MCP_SUMMARIZER_URL
from src.mcp_client import mcp_call


async def _summarize_research_result(
    result: ResearchResult, topic_key: str
) -> ResearchResult:
    """Compress raw content blocks via MCP summarizer before accumulation.

    Concatenates all raw content blocks, sends to the summarizer with the
    topic's research focus as the schema_hint, and returns a new
    ResearchResult with a single summarized block.

    On failure: returns the original result unchanged (graceful degradation).
    """
    if not result.raw_content or not MCP_SUMMARIZER_URL:
        return result

    combined = "\n\n---\n\n".join(result.raw_content)
    schema_hint = RESEARCH_TOPICS.get(topic_key, "")

    summary = await mcp_call(
        MCP_SUMMARIZER_URL,
        "summarize_for_extraction",
        {"content": combined, "schema_hint": schema_hint},
        timeout=120.0,
        sse_read_timeout=300.0,
    )

    if summary is None:
        logger.warning(
            "summarizer_failed_graceful_degradation",
            extra={"topic": topic_key, "raw_blocks": len(result.raw_content)},
        )
        return result

    logger.info(
        "research_content_summarized",
        extra={
            "topic": topic_key,
            "raw_blocks": len(result.raw_content),
            "raw_chars": len(combined),
            "summary_chars": len(summary),
        },
    )

    return ResearchResult(
        raw_content=[summary],
        sources=result.sources,
        summary=result.summary,
    )
```

Modify `_make_research_step`:

```python
def _make_research_step(topic_key: str):
    template = RESEARCH_TOPICS[topic_key]

    async def step(
        checkpoint: ResearchCheckpoint,
        researcher: LoreResearcher,
        publish_fn: Callable | None = None,
    ) -> ResearchCheckpoint:
        zone_name = checkpoint.zone_name.replace("_", " ")
        instructions = "Focus on " + template.format(zone=zone_name, game=GAME_NAME)
        result = await researcher.research_zone(zone_name, instructions=instructions)
        result = await _summarize_research_result(result, topic_key)  # <-- NEW
        _accumulate_research(checkpoint, result, topic_key)
        return checkpoint

    step.__name__ = f"step_{topic_key}"
    return step
```

### Config Changes in `a_world_lore_researcher/src/config.py`

```python
MCP_SUMMARIZER_URL = os.getenv("MCP_SUMMARIZER_URL", "")
```

Empty default means summarization is opt-in — if the URL is not set, `_summarize_research_result` returns the original result unchanged.

### Docker Compose Changes

Add the MCP summarizer service and update the researcher's environment:

```yaml
mcp-summarizer:
  build:
    context: .
    dockerfile: mcp_summarizer/Dockerfile
  ports:
    - "${MCP_SUMMARIZER_PORT:-8007}:8007"
  environment:
    MCP_SUMMARIZER_PORT: "8007"
    LLM_MODEL: ${SUMMARIZER_LLM_MODEL:-openai/gpt-4o-mini}
    OPENROUTER_API_KEY: ${OPENROUTER_API_KEY:-}
  healthcheck:
    test: ["CMD", "python", "-c", "import urllib.request,urllib.error;exec('try:\\n urllib.request.urlopen(\"http://localhost:8007/mcp\")\\nexcept urllib.error.HTTPError as e:\\n exit(0 if e.code==406 else 1)')"]
    interval: 15s
    timeout: 5s
    retries: 3
    start_period: 10s
  restart: unless-stopped

# In world-lore-researcher environment:
#   MCP_SUMMARIZER_URL: http://mcp-summarizer:8007/mcp

# In world-lore-researcher depends_on:
#   mcp-summarizer:
#     condition: service_healthy
```

---

## 7. Error Handling

| Failure | Handling | Rationale |
|---------|----------|-----------|
| LLM rate limit / timeout | Retry 3x with exponential backoff (2s, 4s, 8s) via tenacity | Transient failures are common with API calls (MS-6) |
| LLM persistent failure (3 retries exhausted) | `_summarize_chunk` raises, caught by `map_reduce_summarize` | Let the error propagate to the tool handler |
| Tool-level failure (any exception in `summarize` or `summarize_for_extraction`) | Return original content unchanged. Log warning with error details | Graceful degradation — extraction may still succeed on raw content, and failing the entire pipeline step over a summarization failure is worse than passing raw content (MS-6) |
| Pipeline-level failure (`_summarize_research_result` gets `None` from `mcp_call`) | Return original `ResearchResult` unchanged | Same graceful degradation at the pipeline level (MS-5) |
| Empty content | Return empty string immediately | No work to do |
| Invalid strategy parameter | Default to "semantic" | Sensible fallback, no need to error |

---

## 8. Files Changed

### New Files (mcp_summarizer service)

| File | Purpose |
|------|---------|
| `mcp_summarizer/Dockerfile` | Container definition — python:3.12-slim, includes shared/ |
| `mcp_summarizer/.env.example` | Documents all env vars with defaults |
| `mcp_summarizer/pyproject.toml` | Dependencies: mcp, openai, tiktoken, tenacity, uvicorn |
| `mcp_summarizer/conftest.py` | Adds repo root to sys.path for shared/ |
| `mcp_summarizer/src/__init__.py` | Package marker |
| `mcp_summarizer/src/server.py` | FastMCP server — `summarize` and `summarize_for_extraction` tools |
| `mcp_summarizer/src/config.py` | Env var loading — port, model, API key, chunk defaults |
| `mcp_summarizer/src/logging_config.py` | Structured JSON logging with `service_id: "mcp_summarizer"` in every event |
| `mcp_summarizer/src/chunker.py` | Chunking engine — semantic boundary + token-based fallback |
| `mcp_summarizer/src/summarizer.py` | Map-reduce orchestration — concurrent chunk summarization + merge |
| `mcp_summarizer/src/tokens.py` | Token counting wrapper around tiktoken cl100k_base |
| `mcp_summarizer/prompts/summarize_chunk.md` | General chunk summarization prompt template |
| `mcp_summarizer/prompts/summarize_chunk_extraction.md` | Extraction-aware chunk summarization prompt template |
| `mcp_summarizer/prompts/merge_summaries.md` | Summary merge/reduce prompt template |
| `mcp_summarizer/tests/__init__.py` | Package marker |
| `mcp_summarizer/tests/test_chunker.py` | Unit tests for chunking strategies |
| `mcp_summarizer/tests/test_summarizer.py` | Unit tests for map-reduce orchestration (mocked LLM) |
| `mcp_summarizer/tests/test_tokens.py` | Unit tests for token counting |
| `mcp_summarizer/tests/test_server.py` | Integration tests for MCP tool endpoints |

### Modified Files

| File | Change |
|------|--------|
| `docker-compose.yml` | Add `mcp-summarizer` service block (port 8007). Add `MCP_SUMMARIZER_URL` to `world-lore-researcher` environment. Add `mcp-summarizer` to researcher's `depends_on`. |
| `a_world_lore_researcher/src/pipeline.py` | Add `_summarize_research_result()` function. Modify `_make_research_step()` to call it after `research_zone()` and before `_accumulate_research()`. Add imports for `MCP_SUMMARIZER_URL` and `mcp_call`. |
| `a_world_lore_researcher/src/config.py` | Add `MCP_SUMMARIZER_URL` env var (empty default = opt-in). |
| `a_world_lore_researcher/.env.example` | Add `MCP_SUMMARIZER_URL` documentation. |

---

## 9. Future Work (Out of Scope)

- **Summary caching** — if the same page is crawled by multiple steps or multiple research jobs, the summarizer currently re-summarizes it every time. A cache keyed on content hash would avoid duplicate work. Deferred until profiling shows it matters.
- **Hierarchical/RAPTOR-style recursive summarization** — for content corpora exceeding ~1M tokens, single-level map-reduce may not compress enough. The recursive approach (summarize summaries in a tree) is well-understood but overkill at our current ~200k scale.
- **Per-call model selection** — currently the model is service-wide config. A future `model` parameter on the tools could allow callers to choose cheaper or more capable models per request.
- **Streaming responses** — for very large content, streaming summaries back as they complete (chunk by chunk) could improve perceived latency. Not needed for the pipeline use case where the caller awaits the full result.
- **MCP blueprint** — once the second MCP service with LLM calls exists, extract the shared patterns (prompt loading, OpenAI client, retry, health check) into an MCP blueprint in `.claude/blueprints/mcp-service/`.
