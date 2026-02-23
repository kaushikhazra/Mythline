# Design Dry-Run Report #2

**Document**: `.claude/specs/mcp-summarizer/design.md`
**Reviewed**: 2026-02-23
**Prior**: Dryrun #1 found 2 critical, 4 warnings, 3 observations. All addressed in this revision.

---

## Critical Gaps (must fix before implementation)

None.

---

## Warnings (should fix, may cause issues)

### [W1] `count_tokens()` call outside try/except in both tool functions
- **Pass**: 5 (Failure Path Analysis)
- **What**: In `server.py`, both `summarize` and `summarize_for_extraction` call `count_tokens(content)` for the bypass check BEFORE the try/except block (lines 608 and 635 in the design). If `count_tokens()` raises (e.g., tiktoken encoding error on malformed UTF-8 content, or an unexpected encoding data issue), the exception propagates to FastMCP as an unhandled error. The graceful degradation contract ("return original content on failure") is broken for this code path.
- **Risk**: Malformed content (non-UTF-8 bytes, certain Unicode edge cases) could cause tiktoken to raise, resulting in an MCP error instead of graceful degradation. The pipeline side handles `None` from `mcp_call()`, so no pipeline crash — but the summarizer's own contract is violated.
- **Suggestion**: Move the bypass check inside the try/except block, or wrap the entire function body (including the bypass check) in the try/except.

### [W2] Requirement MS-5 still specifies `mcp_config.json` entry
- **Pass**: 1 (Completeness Check)
- **What**: Requirement MS-5 acceptance criterion states: "Declared in the researcher's `config/mcp_config.json` for discoverability." The design (D10) explicitly decides NOT to do this, with valid rationale (consistency with the storage MCP pattern). However, the requirement document still contains this criterion, creating a documented requirement-design divergence.
- **Risk**: A future implementer reading the requirement would expect to add the mcp_config.json entry. An auditor checking requirements coverage would flag this as unimplemented.
- **Suggestion**: Update `requirement.md` to remove or modify the MS-5 acceptance criterion about mcp_config.json. Either delete the line or change it to: "Summarizer URL configured solely via `MCP_SUMMARIZER_URL` env var (consistent with storage MCP pattern — not added to agent's mcp_config.json)."

---

## Observations (worth discussing)

### [O1] Dryrun #1 findings: all addressed
All 2 critical, 4 warnings, and 1 observation from dryrun #1 have been resolved in this revision:
- C1 (try/except wrappers): Added to both tool functions
- C2 (paragraph break splitting): `_split_by_paragraphs()` with three-tier hierarchy
- W1 (concurrency limiter): Semaphore with `_bounded_summarize` wrapper
- W2 (mcp_config.json): Removed from design, D10 decision documented
- W3 (structured logging): `logging_config.py` module with `service_id`
- W4 (LLM model in logs): `"model": LLM_MODEL` in both log events
- O1 (tiktoken cold start): Pre-download in Dockerfile

### [O2] Semaphore shared across concurrent MCP requests
The `_llm_semaphore = asyncio.Semaphore(5)` is module-level, meaning all concurrent MCP tool calls share the same 5-slot pool. In the current pipeline use case (one research step at a time, sequential), this is a non-issue. But if multiple agents call the summarizer concurrently in the future, they would compete for the same 5 slots. This is actually desirable (protects the LLM API from overload), but worth noting for future scaling considerations.

### [O3] No startup validation for OPENROUTER_API_KEY
If `OPENROUTER_API_KEY` is empty or missing, the service starts successfully but every LLM call will fail with an authentication error. The service will then return original content unchanged (graceful degradation), which may mask a misconfiguration. A startup log warning when the API key is empty would help operators catch this early. Not critical since the service still degrades gracefully.

---

## Summary

| Critical | Warnings | Observations |
|----------|----------|--------------|
| 0        | 2        | 3            |

**Verdict**: PASS WITH WARNINGS — No critical gaps remain. W1 (count_tokens outside try/except) is a minor edge case easily fixed during implementation by moving the bypass check inside the try/except. W2 (requirement-design divergence on mcp_config.json) is a documentation sync issue, not an architectural problem. The design is ready for implementation.
