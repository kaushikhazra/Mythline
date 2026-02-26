# WLR E2E Scorecard — Elwynn Forest (Run 5, round 2 tuning)

**Run**: `elwynn_forest_20260226_022450.json`
**Elapsed**: 443.9s | **Tokens**: 342,884 (orchestrator: 10,502 / workers: 332,382)
**Model**: openrouter:openai/gpt-4o-mini | **Discovery**: enabled

---

## Run Comparison (5 runs)

| Category | Run 1 (pre-tune) | Run 3 (rebalanced) | Run 4 (round 2) | Run 5 (items fix) |
|----------|-------------------|---------------------|-------------------|--------------------|
| NPCs | 11 (5 wrong type) | 10 (all correct!) | 17 (all correct, 0 depth) | 9 (all correct, quest threads good) |
| Factions | 4 (0.0 conf, 0 rels) | 3 (0.9 conf, 0 rels) | 4 (0.9 conf, **4 rels!**) | 4 (0.9 conf, **full matrix!**) |
| Lore | 5 (all history) | 6 (all history) | 6 (5 history + 1 myth) | 7 (5 hist + 1 power + 1 myth) |
| Items | 5 (all wrong type) | 8 (4 correct) | 1 (overcorrected) | **9 (8 correct!)** |
| Sources | 36 (12 domains) | 24 (8 domains) | 33 (9 domains) | 34 (9 domains) |
| Cross-ref conf | {} | {} | all 5 keys | **all 5 keys** |
| Discovery | skipped | self-referencing | 4 correct | 4 correct |

---

## Detailed Evaluation

### 1. Zone Data — 3/4

Narrative arc is 881 chars, covers Defias Brotherhood threat, kobold mines, gnoll attacks,
Stormwind governance issues. Connected zones: westfall, redridge_mountains, duskwood,
burning_steppes — all correct.

### 2. NPCs — 3/4

9 NPCs, all real named individuals with correct roles:
- Marshal Dughan (quest_giver, 3 quests, **has personality data!**)
- Guard Thomas, Deputy Willem — correct military quest givers
- Eagan Peltskinner, Milly Osworth, Sara Timberlain, William Pestle — correct civilian quest givers
- Remy 'Two Times' — correct vendor/quest giver

**Good**: All 9 are real, all have roles, quest threads well-populated (1-5 each).
**Gaps**: Missing Hogger (boss), Billy Maclure, Auntie Bernice. One empty-name entry (parsing
artifact). 0 relationships across all NPCs. Only 1/9 has personality data.

### 3. Factions — 4/4 (up from 2/4!)

Four factions with FULL inter-faction relationship matrix:
- Kingdom of Stormwind: hostile to Defias + Riverpaw, allied to Brotherhood of Northshire
- Defias Brotherhood: hostile to Stormwind + Brotherhood, allied to Riverpaw
- Brotherhood of Northshire: allied to Stormwind, hostile to Defias + Riverpaw
- Riverpaw Pack: hostile to Stormwind + Brotherhood, allied to Defias

Every faction lists its stance toward ALL 3 other factions. This is exactly what was missing
for 3 straight runs. The concrete JSON example in the prompt fixed it.

### 4. Lore — 3/4

7 entries across 3 categories:
- 5 history: First War, Second War, Defias formation, Cataclysm politics, Kobold infestation
- 1 power_source: "Natural Resources of Elwynn Forest"
- 1 mythology: "Cultural Practices in Elwynn Forest"

Category diversity improved! No longer all "history". The explicit Phase 3 search for
mythology/cosmology in the research config produced results.

### 5. Narrative Items — 3/4 (up from 1/4!)

9 items. Evaluation:
- Wanted Poster — real quest item (correct)
- Tome of Divinity — real Paladin quest item (correct)
- The Tome of Divinity — **duplicate** of above (duplicate, not miscategorized)
- Bernice's Necklace — real quest item (correct)
- Maybell's Love Letter — real quest item (correct)
- Gramma Stonefield's Note — real quest item (correct)
- Invisibility Liquor — real quest item (correct)
- Gold Pickup Schedule — real quest item (correct)
- Stonemason's Guild Ring — plausible quest item (correct)

**8/9 are legitimate physical quest items. Zero miscategorized entities** — no NPCs, quests,
locations, or factions leaked through. Only issue is one duplicate (Tome of Divinity x2).

### 6. Source Quality — 3/4

34 sources across 9 domains. 16 official, 8 primary, 10 tertiary (71% authoritative).

### 7. Cross-Reference — 3/4

All 5 confidence keys present: zone=1.0, npcs=0.7, factions=0.9, lore=0.8, narrative_items=0.9.
Final (after caps): zone=1.0, npcs=0.4, factions=0.9, lore=0.8, narrative_items=0.9.
The NPC cap correctly penalizes for sparse depth fields. 0 conflicts detected (could've
flagged missing key NPCs as gaps, but not wrong).

### 8. Discovery — Correct

4 zones: westfall, redridge_mountains, duskwood, burning_steppes. All real connected zones.

---

## Summary

| Category | Run 1 | Run 3 | Run 5 | Notes |
|----------|-------|-------|-------|-------|
| Zone Data | 3/4 | 3/4 | 3/4 | Stable |
| NPCs | 1/4 | 3/4 | 3/4 | All real, quest threads good, depth still sparse |
| Factions | 3/4 | 2/4 | **4/4** | Full inter-faction matrix! |
| Lore | 3/4 | 3/4 | 3/4 | Category diversity improved |
| Items | 1/4 | 2/4 | **3/4** | 8/9 correct, zero miscategorized |
| Sources | 3/4 | 3/4 | 3/4 | Stable |
| Cross-ref | 2/4 | 1/4 | **3/4** | All 5 keys, reasonable scores |
| **Total** | **16/28** | **17/28** | **22/28** | **+6 from baseline** |

---

## Remaining Issues (diminishing returns for gpt-4o-mini)

1. **NPC depth** — personality and motivations mostly empty. This is a research content issue:
   wiki pages for minor Elwynn Forest quest givers don't have personality data. Would improve
   on zones with more prominent NPCs (e.g., Orgrimmar, Stormwind City).
2. **NPC relationships still empty** — the model finds NPCs independently but doesn't infer
   relationships between them. Would need explicit research for "NPC X relationship with NPC Y".
3. **Duplicate items** — "Tome of Divinity" appears twice. A code-level dedup pass would fix this.
4. **One empty-name NPC** — parsing artifact from the model. Schema validation would catch this.

These are model capability limits for gpt-4o-mini, not prompt issues. A more capable model
(gpt-4o, claude-sonnet) would likely produce deeper NPC profiles and fewer duplicates.
