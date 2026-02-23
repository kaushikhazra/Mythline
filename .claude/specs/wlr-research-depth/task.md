# WLR Research Depth Fix — Tasks

## 1. Prompt Files

- [x] Velasari writes `extract_zone.md` prompt for zone metadata extraction in `a_world_lore_researcher/prompts/` — _RD-3_
- [x] Velasari writes `extract_npcs.md` prompt for NPC extraction with personality/role emphasis in `a_world_lore_researcher/prompts/` — _RD-3_
- [x] Velasari writes `extract_factions.md` prompt for faction extraction with ideology/origin emphasis in `a_world_lore_researcher/prompts/` — _RD-3_
- [x] Velasari writes `extract_lore.md` prompt for lore extraction with causal chain emphasis in `a_world_lore_researcher/prompts/` — _RD-3_
- [x] Velasari writes `extract_narrative_items.md` prompt for items extraction with significance filtering in `a_world_lore_researcher/prompts/` — _RD-3_
- [x] Velasari rewrites `research_zone.md` with two-phase research strategy (discover then deep-dive) in `a_world_lore_researcher/prompts/` — _RD-1, RD-2_
- [x] Velasari rewrites `cross_reference.md` with completeness-aware confidence rubric in `a_world_lore_researcher/prompts/` — _RD-5_
- [x] Velasari rewrites `cross_reference_task.md` with cross-category gap detection instructions in `a_world_lore_researcher/prompts/` — _RD-5_
- [x] Velasari deletes `extract_zone_data.md` (replaced by per-category prompts) from `a_world_lore_researcher/prompts/` — _RD-3_
- [x] Velasari writes prompt loading tests for all new/rewritten prompts in `a_world_lore_researcher/tests/test_agent.py` — _RD-1, RD-2, RD-3, RD-5_

## 2. Data Models

- [x] Velasari adds `NPCExtractionResult`, `FactionExtractionResult`, `LoreExtractionResult`, `NarrativeItemExtractionResult` wrapper models to `a_world_lore_researcher/src/agent.py` — _RD-3_
- [x] Velasari adds `EXTRACTION_CATEGORIES` dict mapping category keys to (output_type, prompt_name, token_share) in `a_world_lore_researcher/src/agent.py` — _RD-3_
- [x] Velasari adds `quality_warnings: list[str]` field to `ResearchPackage` in `a_world_lore_researcher/src/models.py` — _RD-7_
- [x] Velasari writes unit tests for new models and EXTRACTION_CATEGORIES in `a_world_lore_researcher/tests/test_agent.py` — _RD-3, RD-7_

## 3. Agent Refactoring

- [x] Velasari adds `_crawl_cache` dict and `_normalize_url()` helper to `LoreResearcher` in `a_world_lore_researcher/src/agent.py` — _RD-6_
- [x] Velasari updates `crawl_webpage` tool with cache check/populate logic in `a_world_lore_researcher/src/agent.py` — _RD-6_
- [x] Velasari replaces `_extraction_agent` with per-category `_extraction_agents` dict in `LoreResearcher.__init__` in `a_world_lore_researcher/src/agent.py` — _RD-3_
- [x] Velasari replaces `extract_zone_data()` with generic `extract_category()` method in `a_world_lore_researcher/src/agent.py` — _RD-3_
- [x] Velasari renames `reset_zone_tokens()` to `reset_zone_state()` (clears cache + tokens) in `a_world_lore_researcher/src/agent.py` — _RD-6_
- [x] Velasari updates `daemon.py` to call `reset_zone_state()` instead of `reset_zone_tokens()` in `a_world_lore_researcher/src/daemon.py` — _RD-6_
- [x] Velasari writes unit tests for URL normalization, cache behavior, extract_category, and agent init in `a_world_lore_researcher/tests/test_agent.py` — _RD-3, RD-6_

## 4. Pipeline Refactoring

- [x] Velasari rewrites `RESEARCH_TOPICS` with two-phase instructions and hostile/antagonist emphasis in `a_world_lore_researcher/src/pipeline.py` — _RD-1, RD-2_
- [x] Velasari rewrites `TOPIC_SCHEMA_HINTS` with MUST PRESERVE directives and proper noun retention in `a_world_lore_researcher/src/pipeline.py` — _RD-4_
- [x] Velasari refactors `step_extract_all` to call `extract_category()` 5 times and assemble `ZoneExtraction` in `a_world_lore_researcher/src/pipeline.py` — _RD-3_
- [x] Velasari adds new imports (`cast`, `FactionStance`, extraction result models) to `a_world_lore_researcher/src/pipeline.py` — _RD-3, RD-5, RD-7_
- [x] Velasari writes unit tests for step_extract_all, RESEARCH_TOPICS content, TOPIC_SCHEMA_HINTS content in `a_world_lore_researcher/tests/test_pipeline.py` — _RD-1, RD-2, RD-3, RD-4_

## 5. Confidence Caps + Quality Warnings

- [x] Velasari implements `_apply_confidence_caps()` function in `a_world_lore_researcher/src/pipeline.py` — _RD-5_
- [x] Velasari wires `_apply_confidence_caps()` into `step_cross_reference` after LLM cross-reference call in `a_world_lore_researcher/src/pipeline.py` — _RD-5_
- [x] Velasari implements `_compute_quality_warnings()` function in `a_world_lore_researcher/src/pipeline.py` — _RD-7_
- [x] Velasari wires `_compute_quality_warnings()` into `step_package_and_send` and adds `quality_warnings` to `ResearchPackage` construction in `a_world_lore_researcher/src/pipeline.py` — _RD-7_
- [x] Velasari writes unit tests for confidence caps, quality warnings, and full pipeline integration in `a_world_lore_researcher/tests/test_pipeline.py` — _RD-5, RD-7_
