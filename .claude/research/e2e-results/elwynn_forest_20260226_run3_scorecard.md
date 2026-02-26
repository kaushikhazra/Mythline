# WLR E2E Scorecard — Elwynn Forest (Run 3, post-tuning)

**Run**: `elwynn_forest_20260226_015741.json`
**Elapsed**: 385.8s | **Tokens**: 358,206 (orchestrator: 8,503 / workers: 349,703)
**Model**: openrouter:openai/gpt-4o-mini | **Discovery**: skipped

---

## Run Comparison (3 runs)

| Category | Run 1 (pre-tune) | Run 2 (over-tuned) | Run 3 (rebalanced) |
|----------|-------------------|---------------------|---------------------|
| NPCs | 11 (5 wrong type) | 0 (guardrails too strict) | 10 (all correct!) |
| Factions | 4 (0.0 conf) | 5 (0.8 conf, 0 relations) | 3 (0.9 conf, 0 relations) |
| Lore | 5 | 6 | 6 |
| Items | 5 (all wrong type) | 12 (all actual items, but generic drops) | 8 (4 quest items, 4 still wrong) |
| Sources | 36 (12 domains) | 20 (4 domains) | 24 (8 domains) |

---

## Detailed Evaluation

### 1. Zone Data — 3/4

Zone overview is solid. Narrative arc (534 chars) mentions Defias Brotherhood fallout, kobold invasions, farmer rivalries, Northshire Valley starting area. Political climate covers Alliance governance, stretched army, Maclure/Stonefield conflict. Phase states now include quest progression phases and Cataclysm changes. Connected zones only lists "elwynn-forest" itself (bug — should be westfall, duskwood, etc.).

### 2. NPCs — 3/4 (up from 1/4!)

**Major improvement.** All 10 NPCs are real, named individuals:
- Marshal Dughan, Marshal McBride, Guard Thomas, Deputy Rainer — all correct quest givers
- Billy Maclure, Auntie Bernice Stonefield, Gramma Stonefield — correct civilian quest givers
- Hogger — correct boss
- Marshal Haggard, Bartlett the Brave — correct minor NPCs

**What improved:**
- Zero miscategorized entities (no factions, creature types, or locations)
- Quest threads populated (most have 1-5 named quests — "The Fargodeep Mine", "Lost Necklace", "WANTED: Hogger")
- Relationships use npc_id properly (Marshal McBride references Marshal Dughan, Billy references Auntie Bernice)

**Remaining gaps:**
- 6/10 have empty personality and motivations (expected for minor NPCs)
- Missing some key NPCs: Brother Sammuel, Sara Timberlain, Remy "Two Times"

### 3. Factions — 2/4 (down from 3/4)

Three factions: Defias Brotherhood, Riverpaw Gnolls, Local Farmers (Maclure/Stonefield). All have sources and 0.9 confidence. But:
- **inter_faction still empty** across all 3 — persistent issue across all runs
- Missing Kingdom of Stormwind, Brotherhood of Northshire, Blackrock Clan
- "Local Farmers" is a stretch as a faction

### 4. Lore — 3/4

Six entries with proper historical progression: Foundation of Stormwind → First War → Second War → Scourge Invasion → Cataclysm → Death Rising. Good causal chains. All have sources. Still all "history" category — P7 fix hasn't taken effect (model ignores mythology/cosmology guidance).

### 5. Narrative Items — 2/4 (up from 1/4)

**Improved but still mixed:**
- Garrick's Head — real quest item (correct)
- The Collector's Ring — real quest item (correct)
- Collar of Princess — real quest item (correct)
- Bernice's Necklace — real quest item (correct)
- Hogger — NPC, not an item (wrong)
- Mother Fang — NPC, not an item (wrong)
- WANTED: 'Hogger' — quest name, not an item (wrong)
- Princess Must Die! — quest name, not an item (wrong)

4/8 are real physical items. The category guardrails are working partially — NPCs/quests still leak through.

### 6. Source Quality — 3/4

24 sources across 8 domains. 12 official, 5 primary, 7 tertiary (71% authoritative). Good.

### 7. Cross-Reference — 1/4 (down from 2/4)

Detected inconsistency (1 conflict) but confidence dict returned **empty** `{}`. This caused final_confidence to only contain npcs=0.00 from caps. The cross-ref agent failed to produce confidence scores — likely an output format issue.

### 8. Discovery — N/A (skipped)

---

## Summary

| Category | Run 1 | Run 3 | Notes |
|----------|-------|-------|-------|
| Zone Data | 3/4 | 3/4 | Stable, connected_zones regressed |
| NPCs | 1/4 | **3/4** | Fixed! All real NPCs, quest threads populated |
| Factions | 3/4 | 2/4 | Fewer factions, inter_faction still empty |
| Lore | 3/4 | 3/4 | Stable, still all "history" |
| Narrative Items | 1/4 | **2/4** | Half correct now, NPCs/quests still leak |
| Source Quality | 3/4 | 3/4 | Stable |
| Cross-Reference | 2/4 | 1/4 | Empty confidence dict — format bug |
| Discovery | N/A | N/A | |
| **Total** | **16/28** | **17/28** | +1 net, but NPCs massively improved |

---

## Remaining Prompt Tuning Notes

### Still open — needs more work:
1. **Faction inter_faction always empty** — 3 runs, always empty. The model may not have enough context about how factions relate to each other. May need the research phase to explicitly search for faction relationships.
2. **Narrative items still include NPCs and quests** — Need even more explicit negative examples ("Hogger is an NPC, not an item. 'Princess Must Die!' is a quest name, not an item.")
3. **Lore all "history"** — Model ignores mythology/cosmology guidance. May be a research content issue — the crawled content is all historical, so the model has no mythology to extract.
4. **Cross-ref confidence dict empty** — Output format issue. The cross_reference agent may need the prompt to emphasize producing the confidence dict with all 5 keys.

### Model limitation note:
Some of these issues may be inherent to gpt-4o-mini's instruction-following capacity. Switching to a more capable model (gpt-4o, claude-sonnet) for extraction agents could improve category boundary adherence without further prompt tuning.
