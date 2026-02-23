# Design Dry-Run Report #1

**Document**: `.claude/specs/mcp-summarizer/design.md`
**Reviewed**: 2026-02-23

---

## Critical Gaps (must fix before implementation)

### [C1] Missing error handling wrapper in server.py tool functions
- **Pass**: 5 (Failure Path Analysis)
- **What**: The design states "Tool-level failure: Return original content unchanged. Log warning with error details" in the error handling table (Section 7). However, the `server.py` code in Section 5 shows `# ... bypass check, then:` followed directly by `map_reduce_summarize(...)` with no try/except. If `map_reduce_summarize` raises (e.g., all chunk LLM retries exhausted via `asyncio.gather`), the exception propagates to FastMCP's error handler, which returns an MCP error — not the original content. The graceful degradation contract is broken.
- **Risk**: Pipeline's `mcp_call()` returns `None` on MCP errors, triggering the pipeline's own graceful degradation. So the pipeline side is safe. But the summarizer's stated contract ("return original content on failure") is not implemented. Callers other than the pipeline (future agents using the tool directly) would get an MCP error instead of fallback content.
- **Fix**: Wrap both tool function bodies in try/except. On exception, log the error and return the original `content` parameter unchanged.

### [C2] Semantic chunking regex does not match paragraph breaks
- **Pass**: 1 (Completeness Check)
- **What**: Requirement MS-3 acceptance criteria states: "Semantic boundary: splits at paragraph breaks, section headers, horizontal rules." The design's `SECTION_PATTERN` regex (`r"(?=^#{1,4}\s|\n-{3,}\n)"`) matches headers and horizontal rules but NOT paragraph breaks (double newlines). Content sections separated only by blank lines (no headers) will be treated as a single monolithic block.
- **Risk**: Wiki pages that use paragraph breaks without headers (common in prose-heavy lore sections) will produce a single oversized section that falls back to token-based chunking, losing the semantic coherence advantage.
- **Fix**: Add double-newline (`\n\n`) as a lower-priority split boundary in the semantic chunker. Strategy: first split by headers/hrules (primary boundaries), then if any resulting section exceeds chunk_size, split that section at paragraph breaks before falling back to token-based.

---

## Warnings (should fix, may cause issues)

### [W1] No concurrency limiter on concurrent LLM calls
- **Pass**: 6 (Concurrency & Ordering)
- **What**: `map_reduce_summarize` uses `asyncio.gather(*tasks)` to summarize all chunks concurrently. A 200k-token input with 8k chunks produces ~25 chunks → 25 simultaneous API calls to OpenRouter. This could trigger rate limiting, especially on cheaper models with lower RPM limits.
- **Risk**: Burst of concurrent requests → 429 rate limit errors → retry storms → slower overall summarization or cascading failures.
- **Suggestion**: Add an `asyncio.Semaphore` to limit concurrent LLM calls (e.g., max 5 concurrent). Pass it to `_summarize_chunk` or use `asyncio.gather` with a bounded wrapper.

### [W2] mcp_config.json entry is misleading
- **Pass**: 3 (Interface Contract Validation)
- **What**: The design adds `"summarizer"` to `a_world_lore_researcher/config/mcp_config.json`. But the pipeline calls the summarizer via `mcp_call()` using `MCP_SUMMARIZER_URL` from `config.py` — not through the pydantic-ai agent toolset. The mcp_config.json only feeds into `load_mcp_config()` for the agent's LLM toolset. The existing `storage` MCP (also called via `mcp_call()`) is NOT in mcp_config.json. Adding `summarizer` but not `storage` is inconsistent.
- **Risk**: Confusing for maintainers. The pydantic-ai agent would see a `summarizer` tool in its toolset that it shouldn't call (summarization is the pipeline's job, not the agent's). Could also cause the agent to attempt summarization calls during its reasoning loop.
- **Suggestion**: Remove the `summarizer` entry from mcp_config.json. The URL is already in config.py. If the intent is documentation/discoverability, add a comment in config.py instead.

### [W3] Missing structured logging setup
- **Pass**: 1 (Completeness Check)
- **What**: Requirement MS-6 states: "All log events include `service_id: 'mcp_summarizer'` for filtering." The design shows `logger.info(...)` calls with structured extras but doesn't include `service_id` in any log event. Additionally, the service structure doesn't include a `logging_config.py` module (unlike agents which have one). The JSON logging infrastructure isn't set up.
- **Risk**: Log events from the summarizer won't be distinguishable from other services in the aggregated log stream.
- **Suggestion**: Add `logging_config.py` to `src/` (or configure logging in `server.py` at startup). Include `service_id: "mcp_summarizer"` as a default extra in all log events.

### [W4] Missing LLM model in log extras
- **Pass**: 1 (Completeness Check)
- **What**: Requirement MS-6 acceptance criteria states logs should include "LLM model used." The `summarization_complete` and `map_phase_started` log events in Section 3.3 include `input_tokens`, `output_tokens`, `compression_ratio`, `num_chunks`, and `strategy` — but not the model name.
- **Risk**: When the model is changed via config, historical logs won't show which model produced which results. Debugging quality issues across model changes becomes harder.
- **Suggestion**: Add `"model": LLM_MODEL` to the `summarization_complete` log extras.

---

## Observations (worth discussing)

### [O1] tiktoken initialization may cause slow first request
The `_encoding = tiktoken.get_encoding("cl100k_base")` at module level in `tokens.py` downloads encoding data on first import if not cached. In a fresh Docker container, the first `count_tokens()` call may take several seconds. Consider adding `RUN python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"` to the Dockerfile to pre-download during build.

### [O2] 5:1 compression ratio is aspirational, not mechanically enforced
MS-2 acceptance criteria states "Compression achieves at least 5:1 ratio." The design doesn't enforce or validate this — it depends on the LLM's summarization quality and the content's compressibility. For the typical input (150k-250k tokens → 5k target), the achieved ratio would be 30:1 to 50:1, far exceeding the 5:1 minimum. For smaller inputs closer to the 5k threshold, the bypass logic prevents unnecessary compression. The 5:1 criterion is effectively satisfied by the default configuration but isn't verified programmatically.

### [O3] asyncio.gather does not cancel in-flight tasks on chunk failure
If one chunk's LLM call fails after 3 retries, `asyncio.gather` raises immediately but other in-flight chunk calls continue running (and consuming tokens) before being garbage collected. This is standard asyncio behavior and doesn't cause correctness issues, but wastes tokens on failed requests. Using `asyncio.TaskGroup` (Python 3.11+) instead would cancel remaining tasks on first failure.

---

## Summary

| Critical | Warnings | Observations |
|----------|----------|--------------|
| 2        | 4        | 3            |

**Verdict**: PASS WITH WARNINGS — the two critical gaps are both about missing implementation details (error handling wrapper, paragraph break splitting) rather than architectural flaws. The core map-reduce architecture, data flow, and pipeline integration are sound. Fix C1 and C2 before implementation; address W1-W4 during implementation.
