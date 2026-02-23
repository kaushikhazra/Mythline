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

### MS-5: Agent-Driven Summarization (Summarize at Source)

**As the** World Lore Researcher agent,
**I want to** have access to a summarization tool during my research runs,
**so that** I can compress large crawled content at the point of research, returning already-summarized content to the pipeline.

**Acceptance Criteria:**
- The summarizer MCP service is added to the agent's `config/mcp_config.json` alongside web search — Pydantic AI exposes `summarize` and `summarize_for_extraction` as agent tools
- The agent's system prompt instructs it to use `summarize_for_extraction` when crawled content is large (~5000+ characters), passing the research topic as `schema_hint`
- The agent autonomously decides when to summarize — small content is left as-is, large content is compressed
- The pipeline does NOT call the summarizer — it just accumulates whatever the agent returns (already summarized at source)
- `_summarize_research_result()` is removed from the pipeline; `_make_research_step()` simplified to `research_zone()` → `_accumulate_research()`
- Summarizer URL configured via `MCP_SUMMARIZER_URL` env var, consumed by `mcp_config.json` via `${MCP_SUMMARIZER_URL}` substitution
- This pattern generalizes across all researcher agents — same MCP config entry, same system prompt section

### MS-6: Structured Logging and Error Resilience

**As a** service operator,
**I want** the summarizer to log its operations and handle failures gracefully,
**so that** I can monitor compression performance and the pipeline doesn't crash on summarization failures.

**Acceptance Criteria:**
- Logs each summarization request: input size (tokens), output size (tokens), compression ratio, chunking strategy used, number of chunks, LLM model used
- On LLM failure (rate limit, timeout, API error): retries with exponential backoff (max 3 retries)
- On persistent failure: returns the original content unchanged (graceful degradation — better to attempt extraction on too-large content than to lose the content entirely)
- All log events include `service_id: "mcp_summarizer"` for filtering

### MS-7: Health Check Endpoint

**As a** Docker operator,
**I want** the MCP Summarizer to expose a `/health` HTTP endpoint,
**so that** Docker can determine service readiness via a simple `curl` command instead of relying on the current hack of hitting `/mcp` and interpreting a 406 error.

**Acceptance Criteria:**
- Exposes a `GET /health` HTTP endpoint on the same port as the MCP service (8007)
- Returns HTTP 200 with JSON body `{"status": "ok"}` when the service is running and ready to accept requests
- Uses FastMCP's `@server.custom_route("/health", methods=["GET"])` decorator (built-in support for custom HTTP routes)
- The `docker-compose.yml` healthcheck for `mcp-summarizer` is updated to use `curl -f http://localhost:8007/health` instead of the current Python urllib hack
- The endpoint does not require authentication or MCP protocol headers
- Response time is under 100ms (no heavy computation — just a readiness signal)
- This pattern should also be applied to `mcp-storage` and `mcp-web-search` for consistency, but those changes are tracked separately

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

The summarizer is added to the agent's `config/mcp_config.json` as an MCP toolset — the agent calls it autonomously during research runs. The `MCP_SUMMARIZER_URL` env var is consumed by `mcp_config.json` via `${MCP_SUMMARIZER_URL}` substitution (same pattern as `MCP_WEB_SEARCH_URL`).

---

## Out of Scope

- **Summary caching** — caching repeated page summaries is a future optimization, not part of the initial build
- **Hierarchical/RAPTOR-style recursive summarization** — overkill at current scale (~200k tokens); single-level map-reduce suffices
- **Changes to the extraction step** — the extraction prompt/agent stay as-is; they just receive smaller input
- **Embedding generation** — the summarizer compresses text, it does not generate embeddings
- **Content crawling** — the summarizer receives already-crawled content, it does not fetch URLs
- **Per-call LLM model selection** — the model is a service-level config, not a per-request parameter
