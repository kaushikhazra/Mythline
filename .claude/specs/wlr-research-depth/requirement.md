# WLR Research Depth Fix — Requirements

## Overview

The World Lore Researcher pipeline runs reliably but produces shallow output (scored 2.65/10 on Westfall). The root cause is a chain of three problems: (1) the research agent crawls category listing pages instead of individual entity wiki pages, so raw content never contains personality/motivation/relationship data; (2) the single-pass extraction merges all 5 categories into one LLM call, causing output token competition that forces breadth over depth; (3) confidence scoring reflects source tier quality, not extraction completeness, so hollow packages ship with inflated confidence.

This spec fixes the research-summarize-extract pipeline to produce story-bible-quality output. No infrastructure changes — all fixes are to prompts, pipeline code, and extraction logic within the existing `a_world_lore_researcher/` agent.

Analysis document: `.claude/research/wlr-westfall-analysis.md`

---

## User Stories

### RD-1: Entity-Level Page Crawling

**As the** research pipeline,
**I want to** crawl individual wiki pages for discovered NPCs and factions (not just category listing pages),
**so that** the raw content contains personality, motivations, relationships, and role data for each entity.

**Acceptance Criteria:**
- After the initial NPC search discovers NPC names from category/overview pages, the agent follows through to crawl individual NPC wiki pages (e.g., `warcraft.wiki.gg/wiki/Edwin_VanCleef`, not just `warcraft.wiki.gg/wiki/Westfall`)
- After the initial faction search discovers faction names, the agent crawls individual faction pages (e.g., `warcraft.wiki.gg/wiki/Defias_Brotherhood`)
- The research prompt explicitly instructs the agent to perform two-phase research: (a) discover entity names from index/overview pages, (b) crawl individual entity pages for depth
- The `RESEARCH_TOPICS` instructions for `npc_research` and `faction_research` are rewritten to mandate individual page crawling
- At least the top 10-15 NPCs per zone get individual page crawls
- At least all named factions get individual page crawls

### RD-2: Antagonist and Boss Coverage

**As the** research pipeline,
**I want to** explicitly search for antagonists, dungeon bosses, and hostile faction leaders separately from friendly quest givers,
**so that** critical story figures like Edwin VanCleef and Vanessa VanCleef are never missed.

**Acceptance Criteria:**
- The NPC research step includes explicit search queries for hostile NPCs, dungeon bosses, and raid bosses associated with the zone
- The faction research step includes explicit search queries for antagonist factions and hostile organizations
- The research prompt instructs: "Search for BOTH friendly and hostile NPCs — quest givers, vendors, bosses, antagonists, and faction leaders"
- For any zone with a dungeon or raid, boss NPCs are researched by name
- Westfall test case: Edwin VanCleef, Vanessa VanCleef, and Defias Brotherhood must all appear in the research output

### RD-3: Per-Category Extraction

**As the** extraction pipeline,
**I want to** run separate LLM extraction passes for each data category (zone, NPCs, factions, lore, narrative items),
**so that** each category gets its own full output token budget and category-specific prompting.

**Acceptance Criteria:**
- The current single `extract_all` step is replaced with per-category extraction: `extract_zone`, `extract_npcs`, `extract_factions`, `extract_lore`, `extract_narrative_items`
- Each extraction pass gets its own LLM call with a category-specific prompt (not the combined `extract_zone_data.md` template)
- Each extraction pass receives only the summarized content relevant to its category (not all 5 sections)
- Each extraction pass has its own output token budget (share of `PER_ZONE_TOKEN_BUDGET`)
- The `ZoneExtraction` model is assembled from the 5 individual extraction results
- Total token usage across all 5 passes stays within the existing `PER_ZONE_TOKEN_BUDGET`

### RD-4: Richer Summarization Schema Hints

**As the** summarization step,
**I want to** use category-specific schema hints that emphasize character depth and relational data,
**so that** the summarizer preserves personality, motivations, inter-NPC relationships, and factional ideology instead of compressing them away.

**Acceptance Criteria:**
- `TOPIC_SCHEMA_HINTS["npc_research"]` explicitly lists personality traits, motivations, NPC-to-NPC relationships, role classification, and phased state as must-preserve fields
- `TOPIC_SCHEMA_HINTS["faction_research"]` explicitly lists ideology, goals, inter-faction stances, key members, and origin story as must-preserve fields
- `TOPIC_SCHEMA_HINTS["lore_research"]` explicitly lists major events, causal chains, named actors, and era/timeline as must-preserve fields
- Schema hints instruct the summarizer to preserve named entity references (proper nouns) even when compressing surrounding text
- Westfall test case: after summarization, the Defias Brotherhood, Edwin VanCleef, Stonemasons' Guild, and the stonemason betrayal event must all survive in the summarized content

### RD-5: Completeness-Aware Confidence Scoring

**As the** cross-reference step,
**I want to** detect missing entities and empty fields when scoring confidence,
**so that** a package with 1 faction and all-empty NPC personality fields does not ship with 0.9 confidence.

**Acceptance Criteria:**
- Cross-reference checks for entity references across categories: if a faction name appears in `zone.narrative_arc` or `zone.political_climate` but not in the `factions` list, faction confidence is penalized
- Cross-reference checks for entity references in NPC quest threads: if an NPC name appears in another NPC's quest thread but is not in the `npcs` list, NPC confidence is penalized
- Empty required fields penalize confidence: if >50% of extracted NPCs have empty `personality`, NPC confidence is capped at 0.4
- Empty required fields penalize confidence: if >50% of extracted NPCs have empty `role`, NPC confidence is capped at 0.4
- Confidence rubric is updated from source-tier-based to completeness-weighted:
  - 0.9-1.0: Multiple sources agree AND all key fields populated AND no cross-category gaps
  - 0.7-0.8: Good source coverage AND most fields populated
  - 0.5-0.6: Source coverage adequate BUT significant empty fields or cross-category gaps
  - 0.3-0.4: Major gaps — missing factions mentioned in narrative, most NPC fields empty
  - 0.0-0.2: Minimal extraction — barely any usable data

### RD-6: URL Deduplication Across Pipeline Steps

**As the** research pipeline,
**I want to** skip re-crawling URLs that were already crawled in previous steps,
**so that** token budget is spent on new content instead of re-processing the same pages.

**Acceptance Criteria:**
- A crawl cache (URL -> content) persists across all research steps (steps 1-5) within a single zone's pipeline run
- When the agent requests a URL that is already in the cache, the cached content is returned without a network call
- Cached content is stored in `ResearchContext` (or equivalent pipeline-level state) — not persisted beyond the zone run
- Source references are still recorded for cached URLs (no source loss)
- Westfall test case: `warcraft.wiki.gg/wiki/Westfall` is crawled at most once, not 8 times
- The dedup applies to the `crawl_webpage` tool — the agent's web search MCP calls are unaffected

### RD-7: Content Quality Thresholds

**As the** packaging step,
**I want to** flag research packages as incomplete when key fields are empty or content is too shallow,
**so that** the validator receives honest quality signals instead of inflated confidence.

**Acceptance Criteria:**
- If `zone.narrative_arc` is under 200 characters, the package is flagged with a `quality_warning: "shallow_narrative_arc"`
- If all extracted NPCs have empty `personality` fields, the package is flagged with `quality_warning: "no_npc_personality_data"`
- If no antagonist/hostile NPCs or factions are present AND the zone has a dungeon, the package is flagged with `quality_warning: "missing_antagonists"`
- Quality warnings are included in the `ResearchPackage` (new field: `quality_warnings: list[str]`)
- Quality warnings do NOT block publishing — the package still goes to the validator, but with honest metadata
- The validator can use quality warnings to request re-research of specific categories

---

## Infrastructure Dependencies

| Dependency | Status | Notes |
|-----------|--------|-------|
| MCP Summarizer | Exists | Schema hints will be updated, no service changes |
| Web Search MCP | Exists | No changes |
| crawl4ai | Exists | No changes |
| RabbitMQ | Exists | No changes |
| Storage MCP | Exists | No changes |

All dependencies already exist. This spec changes only the `a_world_lore_researcher/` agent — prompts, pipeline code, and extraction logic.

---

## Configuration Summary

### Existing Environment Variables (unchanged)

```
PER_ZONE_TOKEN_BUDGET=<max-tokens-per-zone>    # Now split across 5 extraction passes
```

### No New Environment Variables

All changes are to prompts and pipeline logic. No new configuration surface.

---

## Out of Scope

- **Daemon lifecycle** — startup, shutdown, scheduling unchanged
- **RabbitMQ topology** — exchanges, queues, routing keys unchanged
- **Storage schema** — SurrealDB tables unchanged (NPCData already has personality/motivations/relationships fields)
- **Data models** — Pydantic models unchanged except adding `quality_warnings` to `ResearchPackage`
- **Zone progression / discovery** — step 8 unchanged
- **Validator communication** — message format unchanged (quality_warnings is additive)
- **Infrastructure services** — no new Docker containers, no service changes
- **Frontend/UI** — no UI changes
- **Pipeline step count** — the 9-step structure stays; `extract_all` is refactored internally into sub-passes but remains one pipeline step externally
