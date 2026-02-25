# World Lore Researcher — Westfall Quality Analysis

**Date:** 2026-02-23
**Job ID:** job-westfall-002
**Zone:** Westfall (World of Warcraft)
**Depth:** 0 (root zone only)
**Tokens Used:** 226,016 / 500,000 budget

---

## 1. Execution Summary

| Metric | Value |
|--------|-------|
| Total duration | ~9 min 52 sec |
| Pipeline steps completed | 9 (1 skipped: discover_connected_zones at depth=0) |
| Raw content collected | 1,140,520 chars (~285K tokens) |
| Summarized content | 109,329 chars (90% reduction) |
| Research package size | 12,676 bytes |
| Token cost | 226,016 tokens |
| Status messages | 15 (2 from failed job-001, 13 from job-002) |
| Errors | 0 (after budget fix) |

### Step Timing

| Step | Name | Duration | Notes |
|------|------|----------|-------|
| 1 | zone_overview_research | ~39s | Web search + crawl |
| 2 | npc_research | ~56s | Web search + crawl |
| 3 | faction_research | ~60s | Web search + crawl |
| 4 | lore_research | ~65s | Web search + crawl |
| 5 | narrative_items_research | ~51s | Web search + crawl |
| 6 | extract_all | ~5m 17s | Summarization (5 sections) + LLM extraction |
| 7 | cross_reference | ~3s | LLM consistency check |
| 8 | discover_connected_zones | skipped | depth=0 |
| 9 | package_and_send | <1s | Assembly + RabbitMQ publish |

**Observation:** Step 6 dominates at 54% of total time. The summarization sub-steps (5 MCP calls to the summarizer) account for most of it. Extraction itself was fast.

---

## 2. Data Completeness Assessment

### 2.1 Zone Data

| Field | Extracted Value | Expected | Verdict |
|-------|----------------|----------|---------|
| name | "Westfall" | Westfall | CORRECT |
| level_range | 10-60 | 10-60 (post-squish) | CORRECT |
| narrative_arc | "Alliance zone where players encounter the Defias Brotherhood and can explore the Deadmines for loot." | Should cover Defias betrayal, refugee crisis, militia formation, CSI questline, Vanessa VanCleef arc | SHALLOW |
| political_climate | "Alliance territory, with a focus on the conflict against the Defias Brotherhood." | Should mention People's Militia/Westfall Brigade, Stormwind's neglect, homeless refugees, factional tension | SHALLOW |
| access_gating | [] | Correct — no gating | CORRECT |
| phase_states | [] | Cataclysm phasing exists (Sentinel Hill changes, quest progression phases) | MISSING |
| connected_zones | elwynn-forest, duskwood, stranglethorn-vale | Correct zones, but format uses hyphens not underscores | CORRECT (format issue) |
| era | "Classic" | Should indicate multi-era (Classic + Cataclysm revision) or at least note Cataclysm rework | INCOMPLETE |
| confidence | 1.0 | Overconfident given shallow extraction | INFLATED |

**Zone score: 5/10** — Factually correct but surface-level. Westfall's narrative depth (stonemasons' betrayal, political neglect, refugee crisis) is completely absent.

### 2.2 NPCs (10 extracted)

**Extracted NPCs:**
1. Amber Kearnen — quest threads correct
2. Captain Alpert — quest threads correct
3. Captain Danuvin — quest threads correct
4. Farmer Saldean — quest threads correct
5. Hope Saldean — quest threads correct
6. Lieutenant Horatio Laine — quest threads correct (6 quests listed)
7. Marshal Gryan Stoutmantle — quest threads correct (5 quests listed)
8. Salma Saldean — quest threads correct
9. Scout Galiaan — quest threads correct
10. Thoralius the Wise — quest threads correct

**Critical missing NPCs:**
- **Edwin VanCleef** — THE primary antagonist of Classic Westfall/Deadmines. His absence is a major gap.
- **Vanessa VanCleef** — Cataclysm antagonist, daughter of Edwin, mastermind of the new Defias. Huge story figure.
- **Old Blanchy** — Iconic Westfall NPC, beloved by the community, central to a Classic quest and later Revendreth storyline.
- **Two-Shoed Lou** — Mentioned in Horatio's quest threads but not extracted as an NPC.
- **Helix Gearbreaker** — Deadmines boss.
- **Cookie** — Deadmines boss, iconic.
- **Captain Grayson** — Referenced in Scout Galiaan's quest but not extracted.
- **Riverpaw gnoll leaders** — Notable hostile NPCs.

**Field completeness for extracted NPCs:**
- `personality`: EMPTY on all 10
- `motivations`: EMPTY on all 10
- `relationships`: EMPTY on all 10
- `phased_state`: EMPTY on all 10
- `role`: EMPTY on all 10
- `quest_threads`: Populated on all 10 (the only substantive field)
- `faction_ids`: All set to ["alliance"] (correct but generic)

**NPC score: 3/10** — Names and quest threads are correct, but the NPCs are hollow shells. Zero personality, motivation, or relationship data. Missing the most important NPCs in the zone (VanCleefs). The extraction produced a list of quest-givers, not characters.

### 2.3 Factions (1 extracted)

**Extracted:**
- Westfall Brigade — ideology, goals, and source all correct

**Critical missing factions:**
- **Defias Brotherhood** — THE primary antagonist faction of Westfall. This is the most critical single omission in the entire package. It was even mentioned in multiple extracted fields (zone narrative_arc, lore entries) but never extracted as a faction entity.
- **People's Militia** — Classic-era precursor to the Westfall Brigade
- **Stormwind / Alliance** — The governing authority whose neglect caused the crisis
- **Riverpaw Gnolls** — Hostile faction with territorial presence
- **Stonemasons' Guild** — Origin faction of the Defias, critical lore

**Faction score: 2/10** — One faction extracted out of at least 5 significant ones. The Defias Brotherhood being absent despite being mentioned in the zone's own narrative_arc is a clear extraction failure.

### 2.4 Lore Entries (2 extracted)

**Extracted:**
1. "Westfall" (history) — Generic overview about political turmoil and Second War decline. Correct but vague.
2. "The Deadmines" (history) — Correct basic description of Defias stronghold.

**Critical missing lore:**
- **Stonemasons' Guild betrayal** — The foundational lore event: Stormwind nobles refused to pay the stonemasons who rebuilt Stormwind after the First War. This directly caused the Defias Brotherhood.
- **Edwin VanCleef's origin story** — Master stonemason turned bandit lord.
- **Vanessa VanCleef's revenge arc** — Cataclysm storyline where she infiltrates and manipulates Sentinel Hill.
- **The CSI:Westfall questline** — Horatio Laine's murder investigation, one of the most memorable quest chains in WoW.
- **Stormwind refugee crisis** — Cataclysm brought displaced citizens, homelessness, and social commentary.
- **People's Militia formation** — How citizens organized against the Defias.
- **Deadmines dungeon lore** — Boss encounters, pirate ship, VanCleef's plans.

**Lore score: 2/10** — Two generic entries that could be written without any research. None of Westfall's rich, layered narrative is captured.

### 2.5 Narrative Items (1 extracted)

**Extracted:**
- "Westfall Stew" — This is a cooking recipe/quest objective, not a legendary item or narrative artifact. The source URL even contains a typo ("Westfall_Stow"). confidence: 0.9.

**Expected:**
Westfall doesn't have many legendary items per se, but the extraction prompt asks for "narrative objects" which should include:
- **VanCleef's gear/plans** — loot and narrative objects from the Deadmines
- **The Defias plans/documents** — quest items revealing the conspiracy
- **Captain Grayson's lighthouse items** — quest-related narrative objects

**Narrative items score: 1/10** — A cooking recipe classified as a narrative artifact with 0.9 confidence.

### 2.6 Sources (35 URLs)

| Tier | Count | Domains |
|------|-------|---------|
| official | 13 | wowpedia.fandom.com |
| primary | 17 | warcraft.wiki.gg |
| tertiary | 5 | tgexp.com, dungeon.guide, wowclassicdatabase.com, cotuslore.weebly.com, mindseizegame.com, wowwiki-archive.fandom.com |

**Issues:**
- Heavy duplication: warcraft.wiki.gg/wiki/Westfall appears 8 times, warcraft.wiki.gg/wiki/Westfall_Brigade appears 5 times
- 35 URLs but only ~12 unique pages were crawled
- No wowhead.com (one of the best structured data sources for WoW)
- No specific NPC wiki pages crawled (e.g., Edwin_VanCleef, Gryan_Stoutmantle)
- faction_research crawled Westfall_Brigade page 5 times but never found Defias_Brotherhood page (it did find Defias_Brotherhood on wowpedia once at 16:00:11 but apparently didn't extract faction data from it)

**Source score: 5/10** — Good tier distribution, but heavy duplication and missed key pages. The deduplication issue inflates apparent research breadth.

---

## 3. Confidence Analysis

### Reported Confidence Scores

| Category | Score | Justified? |
|----------|-------|------------|
| zone | 1.0 | NO — shallow extraction with missing phase states and era info |
| npcs | 0.7 | PARTIALLY — names correct but all personality/motivation empty |
| factions | 0.9 | NO — only 1 of 5+ factions extracted |
| lore | 0.9 | NO — 2 generic entries, missing all major storylines |
| narrative_items | 0.9 | NO — a cooking recipe with a typo'd URL |

**Verdict:** Confidence scores are systemically inflated. They appear to reflect source tier quality (official/primary sources = high confidence) rather than extraction completeness. A zone with 1 faction and no antagonist NPCs should not have 0.9 faction confidence.

### Cross-Reference Results

The cross-reference step reported:
- `is_consistent: true` (no conflicts detected)
- 0 conflicts

This is technically correct — the extracted data doesn't contradict itself. But "consistent" and "complete" are very different things. The cross-reference step validates internal consistency, not completeness against ground truth. A package with 1 faction and 10 NPCs with empty fields is "consistent" but useless.

---

## 4. Root Cause Analysis

### Why is the extraction so shallow?

**Problem 1: Aggressive summarization lost critical detail**
- 1.14M chars of raw content was reduced to 109K chars (90% reduction) before extraction
- The summarizer optimized for "extraction schema" but the schema hints may be too generic to preserve specific NPC personalities, factional ideology, or narrative arcs
- Per-section budget: 75K / 5 = 15K tokens each — this is tight for rich zones

**Problem 2: Single-pass extraction bottleneck**
- All 5 topics are merged into one LLM extraction call
- The extraction agent must parse ~109K chars and produce structured data for zone + NPCs + factions + lore + narrative items in a single response
- With a PER_ZONE_TOKEN_BUDGET of ~8K output tokens, the LLM likely prioritized breadth (listing names) over depth (filling personality, motivations)

**Problem 3: Research agent searched broadly but not deeply**
- 35 source URLs but many duplicates
- Faction research found the Defias Brotherhood page but the extraction didn't capture it as a faction entity
- NPC research crawled category pages (lists of NPC names) rather than individual NPC pages (which have personality/role data)

**Problem 4: Confidence scoring is source-tier-based, not completeness-based**
- The extraction prompt says 0.7-0.8 = "Single official or multiple primary sources agree"
- Since multiple official sources were found, all categories got high confidence
- No penalty for empty fields or missing entities

---

## 5. Specific Findings & Recommendations

### Finding 1: Empty NPC personality fields (Critical)
**Issue:** All 10 NPCs have empty personality, motivations, relationships, phased_state, and role fields.
**Root cause:** NPC research crawled category listing pages (NPC name lists) rather than individual NPC wiki pages that contain personality/role descriptions.
**Recommendation:** NPC research prompt should instruct the agent to crawl individual NPC pages, not just category listings. The research_zone.md prompt focuses on "names, faction allegiance, personality..." but the agent satisfices by finding name lists.

### Finding 2: Missing Defias Brotherhood faction (Critical)
**Issue:** The primary antagonist faction of Westfall was not extracted despite being mentioned in the zone's own narrative_arc and a Defias_Brotherhood wiki page being crawled.
**Root cause:** The extraction step received summarized faction content that may have lost the Defias Brotherhood entry during summarization. Alternatively, the extraction LLM output was truncated before reaching additional factions.
**Recommendation:** Extraction should be split per-category (zone, NPCs, factions separately) to avoid output token competition. Faction extraction should have its own dedicated pass.

### Finding 3: Missing antagonist NPCs (Critical)
**Issue:** Edwin VanCleef and Vanessa VanCleef — the two most important NPCs in Westfall — are absent.
**Root cause:** Same category listing issue as Finding 1. The agent crawled NPC listing pages that primarily feature quest-giver NPCs, not boss/antagonist NPCs.
**Recommendation:** Research prompt should explicitly instruct: "Search for both friendly and hostile NPCs, quest givers AND antagonists/bosses." The current prompt's neutral language lets the agent stop at quest-giver lists.

### Finding 4: Narrative arc is surface-level (Major)
**Issue:** Zone narrative_arc reads like a tooltip, not a story summary. Missing the political betrayal, class warfare, and revenge themes.
**Root cause:** Summarization compressed zone overview content to 15K chars (from 176K). The extraction LLM then further compressed to a single sentence.
**Recommendation:** narrative_arc should have a minimum content expectation or structured sub-fields (primary_conflict, backstory, resolution, key_themes).

### Finding 5: URL duplication in sources (Minor)
**Issue:** 35 source URLs but only ~12 unique pages. warcraft.wiki.gg/wiki/Westfall crawled 8 times.
**Root cause:** Research agent across different steps re-discovers and re-crawls the same pages.
**Recommendation:** Implement a URL deduplication cache across pipeline steps. If a URL was already crawled in step 1, skip it in step 3 and reuse the cached content.

### Finding 6: Confidence scores don't reflect completeness (Major)
**Issue:** Factions confidence is 0.9 with only 1 of 5+ factions extracted.
**Root cause:** Confidence is based on source tier quality, not extraction completeness. The system doesn't know what it doesn't know.
**Recommendation:** Add completeness heuristics: "If a faction is mentioned in zone narrative_arc but not in the factions list, lower faction confidence." Cross-reference should check for entity references across categories.

### Finding 7: Narrative items quality (Minor)
**Issue:** A cooking recipe extracted as a narrative artifact with 0.9 confidence.
**Root cause:** The extraction prompt's definition of "narrative items" is too broad, and the research step likely found limited results for "legendary items in Westfall" (because there aren't many).
**Recommendation:** The prompt should distinguish between "legendary/artifact items" and "quest items/recipes." For zones without legendary items, the list should be empty rather than padded with irrelevant items.

---

## 6. Overall Quality Score

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Zone metadata | 5/10 | 15% | 0.75 |
| NPC completeness | 3/10 | 25% | 0.75 |
| NPC depth (fields) | 1/10 | 15% | 0.15 |
| Faction coverage | 2/10 | 20% | 0.40 |
| Lore richness | 2/10 | 15% | 0.30 |
| Narrative items | 1/10 | 5% | 0.05 |
| Source quality | 5/10 | 5% | 0.25 |
| **TOTAL** | | **100%** | **2.65/10** |

**Overall verdict: The pipeline runs reliably but the research output is too shallow for storytelling.**

The system correctly identifies that Westfall exists, has the right level range, connects to the right zones, and lists real NPCs with real quest names. But it produces a tourist brochure, not a story bible. For Mythline's drama production agents to write compelling narratives, they need NPC personalities, factional tensions, political backstory, and thematic depth — none of which survived the research-summarize-extract pipeline.

---

## 7. Priority Fixes (Ranked)

1. **Split extraction into per-category passes** — Zone, NPCs, Factions, Lore, Items each get their own extraction call. This prevents output token competition and allows category-specific prompting.

2. **Research NPC individual pages, not just category listings** — Prompt the research agent to "Find and crawl individual wiki pages for the 10-15 most important NPCs" rather than stopping at category index pages.

3. **Explicit antagonist/boss research** — Add an instruction to research hostile NPCs, dungeon bosses, and faction leaders separately from friendly quest givers.

4. **Completeness-aware confidence scoring** — Cross-reference should detect when entities mentioned in one category (e.g., "Defias Brotherhood" in zone narrative_arc) are missing from another (factions list) and lower confidence accordingly.

5. **URL deduplication across pipeline steps** — Cache crawled content and skip re-crawling the same URL in subsequent steps.

6. **Richer summarization schema hints** — Instead of generic "NPCs: names, titles, faction allegiance...", use zone-specific hints that emphasize personality, motivations, and inter-NPC relationships.

7. **Minimum content thresholds** — If narrative_arc is under 200 chars, or if all NPC personality fields are empty, flag the package as incomplete rather than publishing it with inflated confidence.
