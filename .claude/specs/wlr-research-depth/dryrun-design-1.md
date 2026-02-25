# Design Dry-Run Report #1

**Document**: `.claude/specs/wlr-research-depth/design.md`
**Reviewed**: 2026-02-24

---

## Critical Gaps (must fix before implementation)

### [C1] LoreCategory enum mismatch in extract_lore.md prompt
- **Pass**: Pass 7 (Edge Cases & Boundaries)
- **What**: The `extract_lore.md` prompt template (Design Section 4.5) specifies `category: One of: history, mythology, cosmology, prophecy, legend`. However, the `LoreCategory` enum in `models.py` defines: `HISTORY`, `MYTHOLOGY`, `COSMOLOGY`, `POWER_SOURCE`. The values "prophecy" and "legend" are NOT valid enum members, while "power_source" IS valid but is omitted from the prompt.
- **Risk**: When the LLM outputs `category: "prophecy"` or `category: "legend"`, Pydantic validation on `LoreData.category` will fail. With `retries=2`, the agent gets 3 attempts, but if the prompt keeps suggesting invalid values, all 3 attempts fail and the entire lore extraction step raises an exception — killing the pipeline for this zone.
- **Fix**: Change the prompt's category list to match the existing enum: `One of: history, mythology, cosmology, power_source`. If "prophecy" and "legend" are genuinely needed, update the `LoreCategory` enum in `models.py` (and note this as a model change in the Files Changed table).

---

## Warnings (should fix, may cause issues)

### [W1] extract_category() returns BaseModel — callers access category-specific fields without type safety
- **Pass**: Pass 2 (Data Flow Trace) / Pass 3 (Interface Contract Validation)
- **What**: `extract_category()` (Design Section 4.4) returns `BaseModel`. The caller in `step_extract_all` (Section 4.6) does `npcs_result.npcs`, `factions_result.factions`, etc. — accessing fields that don't exist on `BaseModel`.
- **Risk**: Works at runtime (the actual returned object has the field), but mypy/pyright will flag errors, and an IDE won't provide autocomplete. A future refactor could accidentally pass the wrong category name and get a silent attribute error.
- **Suggestion**: Use `@overload` signatures or a generic return type (`T`) bounded to BaseModel. Alternatively, have the caller use `cast()` or a simple type narrowing pattern. At minimum, add a comment noting the intentional duck-typing.

### [W2] FactionStance import missing from pipeline.py
- **Pass**: Pass 5 (Failure Path Analysis)
- **What**: `_compute_quality_warnings()` (Design Section 6.2) references `FactionStance.HOSTILE`, but `pipeline.py` currently does not import `FactionStance` from `src.models`. The design's Files Changed table doesn't mention this import.
- **Risk**: `NameError` at runtime when the quality warnings code path executes.
- **Suggestion**: Add `FactionStance` to the imports in `pipeline.py`. This is a one-line fix but easy to miss if an implementer follows only the design's code snippets.

### [W3] Cross-reference confidence dict key names not contractually specified
- **Pass**: Pass 3 (Interface Contract Validation)
- **What**: `_apply_confidence_caps()` (Section 5.3) expects the confidence dict to contain keys like `"npcs"`. The `step_package_and_send` (Section 6.3) reads `cr_result.confidence`. These keys are produced by the LLM via the cross-reference agent. But the updated `cross_reference.md` (Section 5.1) says "Assign confidence scores for each category" without specifying the exact key names to use. The updated `cross_reference_task.md` (Section 5.2) also doesn't list key names.
- **Risk**: The LLM might use `"npc"` instead of `"npcs"`, `"narrative_item"` instead of `"narrative_items"`, or `"zone_overview"` instead of `"zone"`. The Python caps function would silently skip categories with mismatched keys, and the package would ship with unmodified (potentially inflated) confidence.
- **Suggestion**: Add explicit key names to the cross-reference task prompt: "Use these exact category keys: `zone`, `npcs`, `factions`, `lore`, `narrative_items`."

### [W4] URL deduplication does not normalize URLs
- **Pass**: Pass 7 (Edge Cases & Boundaries)
- **What**: The crawl cache (Section 2.1-2.2) is keyed by exact URL string (`self._crawl_cache[url]`). URL normalization is not applied — the same page accessed with/without trailing slash (`/wiki/Westfall` vs `/wiki/Westfall/`), with different query params, or with fragment identifiers would be treated as different URLs.
- **Risk**: Partial dedup — some duplicate crawls would still occur, wasting token budget. The Westfall analysis showed 8 crawls of the same URL; if some used variant URLs, the dedup wouldn't catch all of them.
- **Suggestion**: Normalize URLs before cache lookup: strip trailing slashes, remove fragments, sort query params. A simple `url = url.rstrip("/").split("#")[0]` covers the most common variants without adding complexity.

### [W5] Crash-resume loses crawl cache — dedup is best-effort within a single process lifetime
- **Pass**: Pass 7 (Edge Cases & Boundaries)
- **What**: The crawl cache is in-memory on the `LoreResearcher` instance. If the daemon crashes mid-pipeline (e.g., during step 3) and restarts, the cache is empty. Steps 3-5 on resume can't benefit from URLs crawled in steps 1-2 of the previous process.
- **Risk**: On crash-resume, the primary dedup benefit (across steps 1-5) is partially lost. The agent will re-crawl URLs from earlier steps.
- **Suggestion**: Acknowledge this as accepted behavior in the design. The requirement says "not persisted beyond the zone run," and the cache is a performance optimization, not a correctness requirement. Add a one-line note: "Cache is best-effort — lost on process restart. Crash-resumed runs may re-crawl some URLs."

### [W6] No confidence cap for zero-NPC or zero-faction scenarios
- **Pass**: Pass 5 (Failure Path Analysis)
- **What**: `_apply_confidence_caps()` only applies caps when `extraction.npcs` is truthy (non-empty list). If the extraction produces zero NPCs, no cap is applied. The LLM cross-reference is solely responsible for assigning low NPC confidence in this case.
- **Risk**: If the LLM assigns high NPC confidence despite zero NPCs (unlikely but possible, especially with weaker models), the package ships with inflated confidence. The requirements (RD-5) only specify caps for ">50% empty fields" — not for zero entities.
- **Suggestion**: Consider adding a zero-entity check: `if not extraction.npcs: capped["npcs"] = min(capped.get("npcs", 0.0), 0.2)`. Same for factions. This is a small addition that prevents a class of LLM errors. If deferred, note it as a known limitation.

### [W7] Per-category extraction results not individually checkpointed
- **Pass**: Pass 5 (Failure Path Analysis)
- **What**: The 5 extraction calls in `step_extract_all` (Section 4.6) run sequentially, but only the final assembled `ZoneExtraction` is saved to `checkpoint.step_data["extraction"]` after all 5 complete. If extraction pass 4 fails, passes 1-3 are lost.
- **Risk**: A transient failure in one extraction category (after Pydantic AI's 3 retries) requires re-running all 5 extraction calls on resume. Token budget is consumed twice for the successful categories.
- **Suggestion**: This is acceptable given that extraction calls are fast (~seconds each vs. minutes for research/summarization). Explicitly note in the design: "Extraction sub-passes are not individually checkpointed. A failure in any pass requires re-running all 5 — acceptable because extraction calls are lightweight compared to research and summarization."

---

## Observations (worth discussing)

### [O1] Token budget for NPCs may be tight for entity-rich zones
The design allocates 30% of PER_ZONE_TOKEN_BUDGET (50,000) = 15,000 output tokens for NPC extraction. With the new depth requirements (personality, motivations, relationships for 10-15 NPCs), each NPC could be ~500-1000 tokens of structured JSON. 15 NPCs at 1000 tokens = 15,000 — right at the limit. For entity-rich zones (capital cities, major quest hubs), the budget could force the LLM to truncate.

This is flagged as an observation, not a warning, because the design's "Future Work" already identifies adaptive token budgets as a deferred improvement.

### [O2] Redundant section headers in extraction prompt content
`_maybe_summarize_sections()` prepends headers (e.g., "## ZONE OVERVIEW") to each section. These headers are included in the content passed to `extract_category()`. But each extraction prompt already specifies its category context (e.g., "Extract all NPCs for zone X"). The header is harmless but slightly redundant — consuming a few tokens of the extraction budget.

### [O3] Semantic change in FactionData.level vocabulary
The existing `extract_zone_data.md` uses "major, minor, subfaction" for faction level. The new `extract_factions.md` (Section 4.5) uses "major_faction, guild, order, cult, military, criminal, tribal." Since `FactionData.level` is a free-form string (no enum validation), both work. But the vocabulary change means data produced before and after this change will use different terms. Downstream consumers should be aware.

---

## Summary

| Critical | Warnings | Observations |
|----------|----------|--------------|
| 1        | 7        | 3            |

**Verdict**: PASS WITH WARNINGS — 1 critical gap (LoreCategory enum mismatch) must be fixed before implementation. The 7 warnings are individually minor but collectively represent missing import, missing normalization, loose contracts, and absent edge-case handling that should be addressed to avoid debugging surprises during implementation.
