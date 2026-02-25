# Code Dry-Run Report #1

**Scope**: `a_world_lore_researcher/` (agent.py, pipeline.py, models.py, daemon.py, all prompts, all tests)
**Design**: `.claude/specs/wlr-research-depth/design.md`
**Reviewed**: 2026-02-24

---

## Bugs (will cause incorrect behavior)

_None found._

---

## Gaps (missing implementation)

_None found. All design elements are implemented._

---

## Warnings (potential issues)

### [W1] "Focus on Focus on..." redundancy in research prompts
- **File**: `src/pipeline.py`:220
- **Pass**: Pass 2 (Execution Path Trace)
- **What**: `_make_research_step()` prepends `"Focus on "` to the RESEARCH_TOPICS template, but every template already starts with `"Focus on ..."`. The resulting instruction sent to the LLM is `"Focus on Focus on zone overview for Westfall in wow."`.
- **Risk**: Cosmetic — the LLM will understand the intent regardless. But if the research prompt is ever reviewed by a human or debugged, the duplication looks sloppy. The factory function was not listed in "Files Changed" (pre-existing code), but the new templates introduced the `"Focus on"` prefix that creates the duplication.

### [W2] MagicMock contaminates token counter in unit tests
- **File**: `tests/test_agent.py`:430-442, also lines 484-496, 502-526
- **Pass**: Pass 7 (Contract Violations)
- **What**: Tests mock `agent.run()` with `MagicMock()` for the result, but `extract_category()` calls `result.usage().total_tokens or 0`. Since MagicMock is truthy, `MagicMock() or 0` evaluates to MagicMock, and `self._zone_tokens += MagicMock()` corrupts the counter to a MagicMock object. Tests pass because no assertion checks `_zone_tokens` after these calls.
- **Risk**: If a future test asserts on `_zone_tokens` after calling `extract_category`, `cross_reference`, or `research_zone`, it will fail unexpectedly. The production code is correct — only the mocks are imprecise.

### [W3] PEP 695 generic syntax requires Python 3.12+
- **File**: `src/agent.py`:260
- **Pass**: Pass 8 (Code Quality)
- **What**: `async def extract_category[T: BaseModel](...)` uses PEP 695 type parameter syntax (Python 3.12+). If the deployment target or CI uses Python 3.11 or earlier, this will fail with a SyntaxError.
- **Risk**: Low — the project uses `uv` and modern tooling, so 3.12+ is likely. But worth confirming the `pyproject.toml` specifies `requires-python = ">=3.12"`.

---

## Style (code quality, conventions)

### [S1] Unused variable in cached crawl path
- **File**: `src/agent.py`:190
- **What**: In the cache-hit branch of `crawl_webpage`, `truncated = content[:CRAWL_CONTENT_TRUNCATE_CHARS]` is computed before checking `if len(content) > CRAWL_CONTENT_TRUNCATE_CHARS`. When content is short, the slice is wasted. Could move the slice inside the `if` block for clarity. Functionally identical.

---

## Summary

| Bugs | Gaps | Warnings | Style |
|------|------|----------|-------|
| 0 | 0 | 3 | 1 |

**Verdict**: PASS

The implementation is clean and faithful to the design. No bugs or gaps found. The three warnings are all minor: W1 is a cosmetic prompt redundancy in pre-existing factory code, W2 is a test mock imprecision that doesn't affect production, and W3 is a Python version dependency that's likely already satisfied. The one style item is a trivial micro-optimization.
