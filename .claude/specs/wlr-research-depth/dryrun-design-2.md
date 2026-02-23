# Design Dry-Run Report #2

**Document**: `.claude/specs/wlr-research-depth/design.md`
**Reviewed**: 2026-02-24
**Context**: Post-fix iteration. All findings from dry-run #1 (1 critical, 7 warnings) were addressed.

---

## Verification of Dry-Run #1 Fixes

All 8 findings from dry-run #1 have been confirmed fixed:

| #1 Finding | Status | Verification |
|------------|--------|--------------|
| [C1] LoreCategory enum mismatch | FIXED | `extract_lore.md` now says `history, mythology, cosmology, power_source` — matches `LoreCategory` enum exactly |
| [W1] BaseModel return type | FIXED | `extract_category` uses `[T: BaseModel]` generic; callers use `cast()` |
| [W2] FactionStance import missing | FIXED | Files Changed table row added for `cast`, `FactionStance`, extraction models |
| [W3] Confidence key names unspecified | FIXED | `cross_reference_task.md` now says `Use these exact category keys: zone, npcs, factions, lore, narrative_items` |
| [W4] URL normalization | FIXED | `_normalize_url()` helper added; `crawl_webpage` uses `cache_key` throughout |
| [W5] Crash-resume cache loss | FIXED | Explicit note added: "cache is best-effort — lost on process restart" |
| [W6] Zero-entity confidence caps | FIXED | `not extraction.npcs → cap 0.2` and `not extraction.factions → cap 0.2` added |
| [W7] No sub-pass checkpointing | FIXED | Explicit note added: "sub-passes not individually checkpointed — acceptable because extraction calls are lightweight" |

---

## Critical Gaps (must fix before implementation)

None.

---

## Warnings (should fix, may cause issues)

### [W1] PEP 695 generic syntax on extract_category requires Python 3.12+
- **Pass**: Pass 7 (Edge Cases & Boundaries)
- **What**: `extract_category[T: BaseModel]` (Section 4.4) uses PEP 695 type parameter syntax, which is a grammar-level change requiring Python 3.12+. This is not enabled by `from __future__ import annotations`. The existing codebase uses `from __future__ import annotations` for string-based annotation features (3.7+), but the union syntax `X | None` in pipeline.py suggests the project targets 3.10+. PEP 695 requires 3.12+.
- **Risk**: If the project's Docker image or CI uses Python 3.10 or 3.11, `extract_category[T: BaseModel]` is a `SyntaxError` at import time. The agent fails to start.
- **Suggestion**: Verify the project's Python version. If < 3.12, use the traditional TypeVar approach: `T = TypeVar("T", bound=BaseModel)` and annotate as `async def extract_category(self, ...) -> T:`. If >= 3.12, the current syntax is preferred.

### [W2] TOPIC_TO_CATEGORY dict defined but unused
- **Pass**: Pass 2 (Data Flow Trace)
- **What**: `TOPIC_TO_CATEGORY` (Section 4.6, line 483-489) maps topic keys to extraction category keys, but the 5 `extract_category()` calls below it hardcode both the category key and the `section_content.get()` topic key. The dict is never referenced.
- **Risk**: An implementer might be confused about whether to use TOPIC_TO_CATEGORY in a loop or follow the explicit calls. Dead code creates ambiguity about the intended pattern.
- **Suggestion**: Either remove the dict (the explicit calls are clearer and support `cast()`), or refactor to use the dict in a loop and handle type narrowing differently. Removing it is simpler.

---

## Observations (worth discussing)

### [O1] Generic return type on extract_category is cosmetic
The `[T: BaseModel]` generic on `extract_category` communicates intent but doesn't provide real type safety — `T` is not constrained by any input parameter (the `category: str` doesn't narrow `T`). Type checkers cannot infer the actual return type from a string argument. The `cast()` calls at the call sites are what actually provide type safety. The generic is harmless but could be replaced with `-> BaseModel` without losing any real type checking. The `cast()` calls are the load-bearing type safety mechanism.

---

## Summary

| Critical | Warnings | Observations |
|----------|----------|--------------|
| 0        | 2        | 1            |

**Verdict**: PASS — no critical gaps. The 2 warnings are minor (Python version compatibility check and dead code cleanup). The design is ready for implementation.
