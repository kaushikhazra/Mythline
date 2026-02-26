# WLR E2E Scorecard — Elwynn Forest (gpt-5-mini)

**Run**: `elwynn_forest_20260226_134522.json`
**Elapsed**: 1038.9s | **Tokens**: 1,251,094 (orchestrator: 17,461 / workers: 1,233,633)
**Model**: openrouter:openai/gpt-5-mini | **Discovery**: enabled

---

## Model Comparison: gpt-4o-mini (Run 5) vs gpt-5-mini

| Metric | gpt-4o-mini (Run 5) | gpt-5-mini | Delta |
|--------|---------------------|------------|-------|
| Elapsed | 443.9s | 1038.9s | +134% slower |
| Total tokens | 342,884 | 1,251,094 | +265% (3.6x) |
| NPCs | 9 | 53 | +489% |
| Factions | 4 | 12 | +200% |
| Lore | 7 | 9 | +29% |
| Items | 9 (1 dup) | 12 (0 dups) | +33% |
| Sources | 34 (9 domains) | 40 (5 domains) | +18% count, fewer domains |
| Conflicts found | 0 | 5 (all real) | Cross-ref actually working |

---

## Detailed Evaluation

### 1. Zone Data — 1/4 (REGRESSION from 3/4)

**Critical issue**: Zone extraction returned an empty shell. Name and confidence (0.8) are
present, but narrative_arc, political_climate, connected_zones, phase_states are ALL empty
strings/lists. The zone category has the smallest token share (0.10 = 7,500 tokens) — gpt-5-mini
may have exhausted the budget on structured output formatting before filling fields, or the model
put zone-level narrative into the lore entries instead.

This is a fixable issue — either bump the zone token share, or adjust the zone prompt to
emphasize filling the narrative_arc and political_climate fields first.

### 2. NPCs — 3/4

**53 NPCs** — massive increase from 9. Nearly all are real named individuals:
- All the previously-missing key NPCs found: Brother Sammuel, Sara Timberlain, Remy "Two Times",
  Billy Maclure, Auntie Bernice, Tommy Joe Stonefield, Maybell Maclure
- 28/53 have personality data (vs 1/9 for gpt-4o-mini)
- 52/53 have roles, 20/53 have motivations
- Quest threads well-populated, relationships present

**Issues**:
- Remy "Two Times" appears twice (also as "William 'Remy' (alias Remy 'Two Times')")
- "Dead names: Erlan Drudgemoor" — extraction artifact in name field
- Some out-of-zone NPCs included: Anduin Wrynn, Turalyon, Genn Greymane, Brann Bronzebeard,
  Garona Halforcen — these are Stormwind City leaders, not Elwynn residents
- "William 'Remen' Marcot" — unclear identity

### 3. Factions — 4/4

**12 factions** — all real, all with ideology, goals, AND full inter-faction relationship matrix:
- Core: Kingdom of Stormwind, Alliance, Stormwind Army, Brotherhood of Northshire
- Antagonists: Defias Brotherhood, Riverpaw Pack, Kobolds, Murlocs, Blackrock Clan, Scourge
- Civilian: Maclure Family, Stonefield Family
- Every faction lists its stance toward ALL other factions
- Sources attached, confidence scores appropriate (0.4-0.9 range)

### 4. Lore — 4/4 (up from 3/4)

**9 entries** across 3 categories with substantial content (973-1,417 chars each):
- 6 history: Defias Brotherhood formation, Vanessa VanCleef's resurgence, Hogger, Goldshire,
  Kobold infestation, Riverpaw Gnolls/Westbrook Garrison
- 1 power_source: Northshire Abbey (foundation, destruction, clerical role)
- 2 mythology: Emerald Nightmare vision, **Goldshire Six Children rumor** (real game mystery!)

The mythology entries are excellent — the Goldshire children is a genuine game mystery/creepypasta
that gpt-4o-mini never found. Real category diversity achieved.

### 5. Narrative Items — 4/4 (up from 3/4)

**12 items — ALL legitimate physical quest items. Zero miscategorization.**
- Bernice's Necklace, Kobold Candles, Gold Dust, Crystal Kelp Fronds, Invisibility Liquor,
  Brass Collar, Maybell's Love Letter, Gramma Stonefield's Note, Argus' Note, Osric's Crate,
  Gold Pickup Schedule, Collector's Ring
- Zero duplicates (gpt-4o-mini had Tome of Divinity x2)
- All have sources (2-3 each)

### 6. Source Quality — 4/4 (up from 3/4)

40 sources: 28 official, 8 primary, 4 tertiary — **90% authoritative** (vs 71% for gpt-4o-mini).
**wowhead.com now included** (was missing in all gpt-4o-mini runs). Only 5 unique domains
(fewer than gpt-4o-mini's 9), but higher quality per domain.

### 7. Cross-Reference — 3/4

Found **5 real conflicts** — all legitimate issues with good resolution suggestions:
1. Faction ID normalization (NPC uses "Stormwind", faction list uses "Kingdom of Stormwind")
2. Duplicate NPC (Remy "Two Times" extracted twice under different names)
3. Extraction artifact ("Dead names: Erlan Drudgemoor" in name field)
4. Factions referenced in lore but missing from factions list (Stonemasons Guild)
5. NPCs referenced in lore/items but missing from NPC list

This is the **first run where cross-ref detected real structural issues** — gpt-4o-mini's
cross-ref reported 0 conflicts in Run 5. However, confidence dict is still empty `{}`.

### 8. Discovery — 4/4

5 zones: stormwind_city, westfall, redridge_mountains, duskwood, dun_morogh.
**Stormwind City now included** (was missing in gpt-4o-mini Run 1). dun_morogh is a minor
stretch (connected via tram, not directly adjacent), but defensible.

---

## Summary

| Category | gpt-4o-mini (Run 5) | gpt-5-mini | Notes |
|----------|---------------------|------------|-------|
| Zone Data | 3/4 | **1/4** | Empty narrative_arc + political_climate (regression) |
| NPCs | 3/4 | 3/4 | 53 NPCs with depth, but duplicates + out-of-zone entries |
| Factions | 4/4 | 4/4 | 12 factions, full matrix |
| Lore | 3/4 | **4/4** | Real mythology (Goldshire children!), 3 categories |
| Items | 3/4 | **4/4** | 12/12 correct, zero miscategorized, zero duplicates |
| Sources | 3/4 | **4/4** | 90% authoritative, wowhead included |
| Cross-ref | 3/4 | 3/4 | Found 5 real conflicts, but confidence dict empty |
| Discovery | (correct) | 4/4 | 5 correct zones including Stormwind City |
| **Total** | **22/28** | **23/28** | +1, but radically different quality profile |

---

## Verdict

gpt-5-mini produces **dramatically richer output** — 5x more NPCs with personality data,
3x more factions with full relationship matrices, genuine mythology, perfect item extraction.
The quality ceiling is clearly higher.

**But**: It costs 3.6x more tokens, takes 2.3x longer, and has a zone data regression
(empty narrative_arc/political_climate). The +1 net score undersells the improvement because
the zone regression (3->1) masks big gains everywhere else. If zone data is fixed, this
would be **25/28**.

### Cost-benefit for production:
- gpt-5-mini at 1.25M tokens/zone is expensive for a daemon that runs continuously
- The depth improvements (53 NPCs, 12 factions, real mythology) matter for storytelling quality
- Zone data regression is fixable (bump token share or prompt adjustment)

### Recommendation:
Fix the zone data extraction (bump zone token_share from 0.10 to 0.15), retest once.
If zone scores 3+/4, adopt gpt-5-mini as the production model. The depth difference is
worth the token cost for a storytelling system.
