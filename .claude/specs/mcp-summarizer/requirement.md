# MCP Summarizer Service — Requirements

## Overview

Standalone MCP service that compresses large text content into concise, domain-aware summaries using a map-reduce pattern. Solves context window overflow in researcher agent pipelines, where 10-18 crawled web pages (~150k-250k tokens) must be condensed to fit within an LLM's context window for structured extraction.

The service exposes two MCP tools: a general-purpose `summarize` tool and an extraction-targeted `summarize_for_extraction` tool. It handles chunking, per-chunk summarization, and summary merging internally — callers send content in, summaries come back. The service uses its own LLM connection (via OpenRouter) so callers don't spend their own token budgets on compression.

The service follows Mythline's MCP conventions: FastMCP server, StreamableHTTP transport, Docker container, environment-based configuration.

---

## User Stories

### MS-1: General Map-Reduce Summarization

**As a** Mythline agent,
**I want to** send large text content to an MCP tool and receive a compressed summary,
**so that** the content fits within my LLM's context window for downstream processing.

**Acceptance Criteria:**
- Exposes a `summarize` MCP tool accepting: content (string), max_output_tokens (int, optional), focus_areas (list of strings, optional)
- Chunks the input content into segments that fit within the summarization LLM's context window
- Summarizes each chunk independently (map phase)
- Merges chunk summaries into a single coherent summary (reduce phase)
- If focus_areas are provided, the summarizer emphasizes those topics during summarization (e.g., ["NPCs", "factions", "lore events"])
- Returns a single string summary
- If the input content already fits within the target output size, returns it unchanged (no unnecessary compression)

### MS-2: Extraction-Targeted Summarization

**As a** researcher pipeline,
**I want to** summarize content with awareness of the structured fields I need to extract,
**so that** domain-relevant details (NPC names, faction relationships, lore events) are preserved while boilerplate is discarded.

**Acceptance Criteria:**
- Exposes a `summarize_for_extraction` MCP tool accepting: content (string), schema_hint (string describing the target extraction schema), max_output_tokens (int, optional)
- The schema_hint tells the summarizer what categories of information matter (e.g., "zone metadata, NPCs with faction allegiances, faction hierarchy, lore events, narrative items")
- Summarization preserves all details matching the schema hint — names, relationships, specific data points
- Summarization aggressively discards: navigation menus, cookie banners, site chrome, repetitive content, unrelated advertisements
- Returns a single string summary optimized for downstream structured extraction
- Compression achieves at least 5:1 ratio while retaining extraction-relevant detail

### MS-3: Configurable Chunking Strategies

**As a** service operator,
**I want** the summarizer to chunk content intelligently based on its structure,
**so that** chunks preserve semantic coherence rather than splitting mid-paragraph or mid-section.

**Acceptance Criteria:**
- Supports two chunking strategies:
  - **Semantic boundary**: splits at paragraph breaks, section headers, horizontal rules (default)
  - **Token-based**: splits at fixed token boundaries with configurable overlap (fallback for unstructured content)
- Chunking strategy is selectable per call via an optional `strategy` parameter (defaults to semantic)
- Semantic chunking respects markdown structure: headers (`#`, `##`), horizontal rules (`---`), and paragraph breaks
- Each chunk includes sufficient context (overlap or header propagation) to avoid orphaned references
- Chunks that exceed the summarization LLM's context window are further split using token-based fallback
- Default chunk size target: 8,000 tokens with 500-token overlap (configurable via env vars)

### MS-4: LLM-Agnostic Summarization

**As a** service operator,
**I want** the summarization LLM to be configurable via environment variables,
**so that** I can switch between models (gpt-4o-mini, gemini-2.0-flash, claude-3.5-haiku) without code changes.

**Acceptance Criteria:**
- LLM model configured via `LLM_MODEL` env var (OpenRouter format: `provider/model-name`)
- API key configured via `OPENROUTER_API_KEY` env var
- The service calls the LLM directly (via OpenRouter/litellm or pydantic-ai), not through another MCP service
- Model choice is transparent to callers — the MCP tool interface is the same regardless of backend model
- Default model is a fast, cheap option suitable for summarization (not a frontier reasoning model)

### MS-5: Pipeline Integration via MCP Tool Calls

**As the** World Lore Researcher pipeline,
**I want to** call the summarizer MCP service after each research step to compress crawled content before accumulation,
**so that** the extraction step (step 6) receives ~25k tokens of summaries instead of ~200k tokens of raw content.

**Acceptance Criteria:**
- The pipeline calls the summarizer via `mcp_call()` (StreamableHTTP, same pattern as storage/search MCP calls)
- Summarization happens at the pipeline orchestration level (inside `_accumulate_research()`), not inside the research agent's reasoning loop
- Each research step's raw content blocks are summarized with the step's topic as focus area
- The summarized content replaces raw content in `checkpoint.step_data["research_raw_content"]`
- The research agent continues to see truncated content (5k chars) during its own reasoning — no change to agent behavior
- Summarizer URL configured via `MCP_SUMMARIZER_URL` env var in the researcher's config (not added to agent's `mcp_config.json` — consistent with storage MCP pattern where pipeline-called services use `mcp_call()` directly)

### MS-6: Structured Logging and Error Resilience

**As a** service operator,
**I want** the summarizer to log its operations and handle failures gracefully,
**so that** I can monitor compression performance and the pipeline doesn't crash on summarization failures.

**Acceptance Criteria:**
- Logs each summarization request: input size (tokens), output size (tokens), compression ratio, chunking strategy used, number of chunks, LLM model used
- On LLM failure (rate limit, timeout, API error): retries with exponential backoff (max 3 retries)
- On persistent failure: returns the original content unchanged (graceful degradation — better to attempt extraction on too-large content than to lose the content entirely)
- All log events include `service_id: "mcp_summarizer"` for filtering

---

## Infrastructure Dependencies

| Dependency | Status | Notes |
|-----------|--------|-------|
| OpenRouter API | Exists | LLM API gateway — used for summarization calls |
| Docker | Exists | Container orchestration |
| FastMCP | Exists | MCP server framework (already in use by storage + web search services) |
| crawl4ai | Exists | Not a direct dependency — the summarizer receives already-crawled content |

No new external infrastructure required. The MCP Summarizer is a stateless service that only needs an LLM API key.

---

## Configuration Summary

### Environment Variables

```
MCP_SUMMARIZER_PORT=<service-port>              # Default: 8007
LLM_MODEL=<openrouter-model-id>                 # Default: openai/gpt-4o-mini
OPENROUTER_API_KEY=<api-key>                     # Required
DEFAULT_CHUNK_SIZE_TOKENS=<tokens-per-chunk>     # Default: 8000
DEFAULT_CHUNK_OVERLAP_TOKENS=<overlap>           # Default: 500
DEFAULT_MAX_OUTPUT_TOKENS=<target-summary-size>  # Default: 5000
```

### Agent-Side Configuration

```
# In researcher's .env:
MCP_SUMMARIZER_URL=http://mcp-summarizer:8007/mcp
```

The summarizer is called by the pipeline via `mcp_call()`, not through the agent's LLM toolset. It is NOT added to `config/mcp_config.json` (consistent with the storage MCP pattern).

---

## Out of Scope

- **Summary caching** — caching repeated page summaries is a future optimization, not part of the initial build
- **Hierarchical/RAPTOR-style recursive summarization** — overkill at current scale (~200k tokens); single-level map-reduce suffices
- **Changes to the extraction step** — the extraction prompt/agent stay as-is; they just receive smaller input
- **Embedding generation** — the summarizer compresses text, it does not generate embeddings
- **Content crawling** — the summarizer receives already-crawled content, it does not fetch URLs
- **Per-call LLM model selection** — the model is a service-level config, not a per-request parameter
