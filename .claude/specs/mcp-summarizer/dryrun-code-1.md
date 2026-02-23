# Code Dry-Run Report #1

**Scope**: `mcp_summarizer/src/`, `a_world_lore_researcher/src/pipeline.py`, `a_world_lore_researcher/src/config.py`, `docker-compose.yml`
**Design**: `.claude/specs/mcp-summarizer/design.md`
**Reviewed**: 2026-02-23

---

## Bugs (will cause incorrect behavior)

### [B1] `chunk_token_based` infinite loop when `overlap >= chunk_size`
- **File**: `mcp_summarizer/src/chunker.py`:137
- **Pass**: Pass 2 (Execution Path Trace)
- **What**: When `overlap >= chunk_size`, the step `start = end - overlap` can result in `start` staying the same or moving backwards, causing an infinite loop.
- **Impact**: Service hangs forever on a single request. With default config (chunk_size=8000, overlap=500) this won't trigger, but a misconfigured env var or a future caller passing `overlap=chunk_size` would hang the process.
- **Fix**: Guard the step advancement:
  ```python
  step = max(chunk_size - overlap, 1)
  start += step
  ```
  Or validate at entry: `overlap = min(overlap, chunk_size - 1)`.

### [B2] `_summarize_research_result` passes unformatted RESEARCH_TOPICS template as `schema_hint`
- **File**: `a_world_lore_researcher/src/pipeline.py`:176
- **Pass**: Pass 2 (Execution Path Trace)
- **What**: `schema_hint = RESEARCH_TOPICS.get(topic_key, "")` retrieves the raw template string which contains `{zone}` and `{game}` placeholders (e.g., `"zone overview for {zone} in {game}: level range, ..."`). These unformatted placeholders are sent as the `schema_hint` to the summarizer. The summarizer prompt template does not have `{zone}` or `{game}` slots, so the placeholders pass through as literal text — the schema_hint will read "zone overview for {zone} in {game}" instead of "zone overview for Elwynn Forest in wow".
- **Impact**: The summarizer receives a schema hint with literal `{zone}` and `{game}` instead of the actual zone/game names. Summarization quality is reduced but not broken — the LLM can still infer intent from the surrounding text. Not a crash, but produces suboptimal compression.
- **Fix**: Format the template before passing it as schema_hint:
  ```python
  zone_name = result.raw_content  # Not available here — need to pass zone_name
  ```
  Better approach: pass `topic_key` and `zone_name` to `_summarize_research_result`, or use just the topic description without placeholders. Simplest fix — strip the template to a static description:
  ```python
  # In _make_research_step, pass formatted instructions as well:
  result = await _summarize_research_result(result, topic_key, zone_name)
  ```
  And in `_summarize_research_result`:
  ```python
  async def _summarize_research_result(
      result: ResearchResult, topic_key: str, zone_name: str = ""
  ) -> ResearchResult:
      ...
      template = RESEARCH_TOPICS.get(topic_key, "")
      schema_hint = template.format(zone=zone_name, game=GAME_NAME) if template else ""
  ```

---

## Gaps (missing implementation)

### [G1] `chunk_semantic` `overlap` parameter is accepted but never used
- **File**: `mcp_summarizer/src/chunker.py`:25
- **Pass**: Pass 1 (Design Conformance)
- **What**: `chunk_semantic()` accepts an `overlap` parameter but only passes it through to `chunk_token_based()` when falling back. The semantic chunking itself does no overlapping between chunks. The design specifies the parameter for the function signature but does not define semantic overlap behavior. This means when `strategy="semantic"` (the default), the `DEFAULT_CHUNK_OVERLAP_TOKENS=500` config value has no effect on semantic chunks — only on token-based fallback sub-chunks within oversized sections.
- **Design ref**: Section 2.1 — the design code shows the same behavior (overlap only used in token-based fallback). This is design-conformant but worth noting: the overlap config parameter is misleading for the primary chunking strategy.

---

## Warnings (potential issues)

### [W1] Module-level `asyncio.Semaphore` may not work across event loops
- **File**: `mcp_summarizer/src/summarizer.py`:28
- **Pass**: Pass 6 (Concurrency & Async Correctness)
- **What**: `_llm_semaphore = asyncio.Semaphore(MAX_CONCURRENT_LLM_CALLS)` is created at module import time. If the module is imported before an event loop is running (which is typical), the semaphore is bound to no loop. In Python 3.10+ this is fine — `asyncio.Semaphore` no longer binds to a specific loop at creation. But if FastMCP or uvicorn creates a new event loop internally, a semaphore created outside that loop could cause issues in older Python. Since the project targets Python 3.12+, this is safe but worth documenting.
- **Risk**: No risk on Python 3.12+. Low risk item — only relevant if the runtime setup changes significantly.

### [W2] Module-level `AsyncOpenAI` client created at import time
- **File**: `mcp_summarizer/src/summarizer.py`:21-24
- **Pass**: Pass 5 (Resource Management)
- **What**: `client = AsyncOpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)` is instantiated at module import time. If `OPENROUTER_API_KEY` is empty (the default), the client is created with an empty API key. The `openai` SDK accepts this at construction time but will fail on first request with an authentication error. This is fine for graceful degradation (the tool-level try/except catches it) but the first indication of misconfiguration comes only when a request is made, not at startup.
- **Risk**: Silent misconfiguration — the service starts healthy but every summarization request fails. The healthcheck passes (it checks the MCP endpoint, not LLM connectivity). A startup validation log would help operators catch this early.

### [W3] `_summarize_research_result` gets `str` from `mcp_call` but `mcp_call` can return `dict | list | str | None`
- **File**: `a_world_lore_researcher/src/pipeline.py`:178-184
- **Pass**: Pass 7 (Contract Violations)
- **What**: `mcp_call()` returns `dict | list | str | None`. The code checks `if summary is None:` but doesn't verify the return is actually a `str`. If the MCP tool returns a structured response (e.g., the SDK wraps it), `summary` could be a `dict`. Passing a `dict` to `ResearchResult(raw_content=[summary])` would put a dict in a list expected to contain strings.
- **Risk**: Low — the `summarize_for_extraction` tool returns `str` by design (D3), and `_parse_result` in `mcp_client.py` returns the single TextContent string directly. But a defensive `str(summary)` cast or type check would be more robust.

### [W4] `reduce_pass` log event doesn't include `model` field
- **File**: `mcp_summarizer/src/summarizer.py`:109-116
- **Pass**: Pass 8 (Code Quality)
- **What**: The `map_phase_started` and `summarization_complete` log events include `"model": LLM_MODEL` in extras, but the `reduce_pass` log event does not. This is inconsistent — if debugging which model was used during a reduce pass, the model field is missing.
- **Risk**: Minor observability gap. Not a bug but inconsistent with the design's intent (D11: "Log extras include the LLM model name for debugging quality changes across model switches").

---

## Style (code quality, conventions)

### [S1] Exception info captured via `str()` loses traceback detail
- **File**: `mcp_summarizer/src/logging_config.py`:33
- **What**: `log_entry["exception"] = str(record.exc_info[1])` captures only the exception message, not the full traceback. The `exc_info=True` in the log call generates a full traceback, but the JSON formatter discards it in favor of just the string representation. For production debugging, the full traceback is valuable. Consider using `self.formatException(record.exc_info)` to capture the full traceback string.

---

## Summary

| Bugs | Gaps | Warnings | Style |
|------|------|----------|-------|
| 2    | 1    | 4        | 1     |

**Verdict**: PASS WITH WARNINGS — B1 (infinite loop) is a latent bug that doesn't trigger with default config but should be fixed. B2 (unformatted schema_hint) reduces summarization quality but doesn't crash. No critical failures in the happy path.
