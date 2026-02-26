# WLR E2E Scorecard — Elwynn Forest

**Run**: `elwynn_forest_20260226_013535.json`
**Elapsed**: 420.5s | **Tokens**: 416,686 (orchestrator: 8,378 / workers: 408,308)
**Model**: openrouter:openai/gpt-4o-mini | **Discovery**: skipped

---

## Scoring Scale

| Score | Meaning |
|-------|---------|
| 0 | Missing or broken |
| 1 | Present but mostly wrong/empty |
| 2 | Partial — some real data, significant gaps |
| 3 | Good — mostly accurate, minor gaps |
| 4 | Excellent — comprehensive and accurate |

---

## Detailed Evaluation

### 1. Zone Data — 3/4

**Accurate**:
- Name, game, level range (1-30 post-Cataclysm scaling) all correct
- Narrative arc (1,053 chars) is a real, coherent description — mentions kobolds, Defias Brotherhood, Orc invasions, resilience themes — all accurate
- Political climate accurately covers Stormwind governance, Riverpaw gnolls, Defias remnants, farmer tensions about taxes and neglect
- Connected zones include Duskwood, Redridge Mountains, Westfall — all correct

**Gaps**:
- **Missing Stormwind City** as a connected zone — it's the most important connection (the capital city is physically adjacent)
- Phase states empty — Elwynn has minimal phasing in Classic, but post-Cataclysm Northshire has phased content (Blackrock orc invasion). Minor gap.
- Era is vague: "Classic and subsequent expansions from Cataclysm onwards" — could be more specific about what changed per expansion

### 2. NPCs — 1/4

**Critical category error**: 5 out of 11 "NPCs" are not NPCs at all:
- **Defias Brotherhood** — this is a FACTION, not an NPC
- **Kobolds** — creature TYPE, not a specific NPC
- **Gnolls** — creature TYPE, not a specific NPC
- **Murlocs** — creature TYPE, not a specific NPC
- **Northshire Abbey** — this is a LOCATION, not an NPC

**Real NPCs found (6 of 11)**:
- Marshal Dughan — correct, quest giver in Goldshire
- Marshal McBride — correct, first quest giver in Northshire
- Guard Thomas — correct, quest giver at eastern bridge
- Deputy Rainer — correct, quest giver near western border
- Hogger — correct, famous gnoll boss (but listed as faction "Riverpaw Gnolls" which is good)
- Goldtooth — correct kobold boss in Fargodeep Mine (but listed as faction "Gnolls" — should be Kobolds)

**Other issues**:
- `quest_threads` empty for ALL NPCs — this is a significant gap for a quest-driven zone
- `npc_id` fields in relationships all empty — references use text descriptions instead of actual NPC IDs
- `faction_ids` use descriptive text ("Alliance", "Hostile creatures") instead of linking to extracted faction data
- Missing key NPCs: Brother Sammuel, Sara Timberlain, Remy "Two Times", Gramma Stonefield, Billy Maclure, "Auntie" Bernice Stonefield

### 3. Factions — 3/4

**Accurate**:
- **Stormwind Army** — real faction, accurate ideology about protecting the kingdom
- **Defias Brotherhood** — real faction, accurate ideology about worker grievances and Stormwind rebuilding
- **Brotherhood of Northshire** — real clerical order, accurate goals about training adventurers
- **Riverpaw Gnolls** — real gnoll clan, accurate hostile stance with Stormwind
- Inter-faction relations make sense (Defias hostile to Stormwind, Riverpaw hostile, Brotherhood allied)
- Ideology and goals are meaningful, not generic filler

**Gaps**:
- All factions have **0.0 confidence** and **empty source lists** — this is a data pipeline issue (sources not propagated to faction extraction output)
- Missing Stormwind City Guard (distinct from Army in-game)

### 4. Lore — 3/4

**Accurate**:
- **Elwynn Forest Overview** — good overview of the forest's role and geography
- **First War** — correct that Elwynn was burned during the Orc invasion, then regrew
- **Foundation of Stormwind** — correct about Arathi bloodline from Stromgarde
- **The Rise of the Defias Brotherhood** — correct about workers cheated during rebuilding

**Minor issues**:
- **The Scourge Invasion** — overstated. The Scourge invasion of Elwynn was a temporary pre-Wrath world event, not a permanent lore fixture. Including it as a standalone lore entry overemphasizes its role.
- All categories are "history" — missing mythology, cosmology, power source categories
- Eras are vague ("Present Era", "Historical Event", "Centuries ago")

### 5. Narrative Items — 1/4

**Fundamentally misidentified category**: NONE of the 5 items are actual narrative items (weapons, artifacts, quest objects):
- **Northshire Abbey** — LOCATION
- **Goldshire** — LOCATION
- **Hogger** — NPC
- **Defias Brotherhood** — FACTION
- **Mirror Lake** — LOCATION

Real narrative items in Elwynn Forest include:
- Hogger's Claw (Cataclysm quest item)
- Bernice's Necklace (quest item from Gramma Stonefield chain)
- Gold Dust (collected from kobolds)
- Marshal Dughan's Reports
- Wine and cheese from the Maclure/Stonefield feud

The extraction model completely misunderstood what "narrative items" means in this schema.

### 6. Source Quality — 3/4

**Good**:
- 36 sources across 12 domains — good diversity
- 13 official (wowpedia.fandom.com) + 8 primary (warcraft.wiki.gg) = 21 authoritative out of 36 (58%)
- Major authoritative sources present and used correctly
- No obviously hallucinated URLs

**Concerns**:
- 15 tertiary sources (42%) — some questionable: "alternativebfastory.wordpress.com", "worldofwarcraft.video.tm", "tgexp.com"
- Missing wowhead.com which is a major primary source for quest/NPC data

### 7. Cross-Reference — 2/4

**Good**:
- Successfully ran, reported consistent with 0 conflicts
- NPC confidence at 0.5 — reasonable given the category errors

**Issues**:
- Factions at 0.0 confidence was correctly identified but not flagged as a conflict/issue
- Narrative items at 1.0 confidence — WRONG. Should have flagged that all items are misidentified (locations/NPCs/factions, not actual items)
- 0 conflicts reported despite significant category errors — cross-reference failed to detect structural issues
- The cross-ref seems to only check internal consistency (do references match), not whether entities are correctly categorized

### 8. Discovery — N/A (skipped)

---

## Summary

| Category | Score | Notes |
|----------|-------|-------|
| Zone Data | 3/4 | Good narrative arc and political climate; missing Stormwind City connection |
| NPCs | 1/4 | 5/11 are not NPCs (factions, creature types, locations); no quest threads |
| Factions | 3/4 | All 4 are real factions with accurate relations; empty sources and 0.0 confidence |
| Lore | 3/4 | Good historical lore; all "history" category, missing mythology/cosmology |
| Narrative Items | 1/4 | All 5 misidentified — locations/NPCs/factions listed as items |
| Source Quality | 3/4 | Good official/primary mix; some tertiary junk |
| Cross-Reference | 2/4 | Ran but failed to detect category misidentification |
| Discovery | N/A | Skipped |
| **Total** | **16/28** | |

---

## Prompt Tuning Notes

_What needs to change in orchestrator/worker prompts based on this run:_

### P1 — NPC extraction prompt needs entity type guardrails
The NPC extraction prompt must explicitly state: "Only include individual named NPCs — specific characters with names. Do NOT include creature types (Kobolds, Gnolls, Murlocs), factions (Defias Brotherhood), or locations (Northshire Abbey). Each NPC must be a single named individual who exists in the game world." Also emphasize capturing `quest_threads` — they are all empty, but quest connections are the primary reason NPCs exist in Elwynn.

### P2 — Narrative items prompt needs category definition
The extraction prompt completely fails to define what a narrative item is. Add: "A narrative item is an in-game object, weapon, artifact, quest item, or collectible with narrative significance. NOT locations, NPCs, or factions. Examples: quest rewards, key items, lore books, named weapons." The current prompt likely just says "narrative items" without distinguishing from other entity types.

### P3 — Faction extraction not propagating sources
All 4 factions have empty `sources` lists despite good data quality. The extraction prompt or the extraction agent is not including source references in its structured output. Check if the prompt asks for sources on each faction entry.

### P4 — NPC relationship IDs not populated
All NPC relationships have empty `npc_id` fields and use text descriptions instead. The prompt should instruct the model to use the NPC name as the ID when referencing other NPCs, or cross-link to extracted NPC entries.

### P5 — Cross-reference should validate entity categories
The cross-ref agent should check: "Is each NPC actually an individual NPC? Is each narrative item actually an item?" Currently it only checks internal consistency (do references match), not whether entities are correctly categorized.

### P6 — Research agent should prioritize quest databases
The research agent found zone overview and faction data well but missed quest-level detail. The research instructions should emphasize searching for quest chains, quest NPCs, and quest items — not just zone overviews. Adding wowhead.com as a preferred search target would help.

### P7 — Lore categories too narrow
All 5 lore entries are "history". The prompt should encourage the model to look for mythology, cosmology, and power source categories too. Elwynn has magical lore (Mirror Lake, Tower of Azora, mage trainers) that wasn't captured.
