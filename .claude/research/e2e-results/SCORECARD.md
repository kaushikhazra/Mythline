# WLR E2E Scorecard Template

Velasari reads the JSON output from `e2e_smoke.py` and produces this scorecard.
Each run gets a copy with scores filled in.

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

## Categories

### 1. Zone Data (0-4)

- Narrative arc: Is it a real, coherent description of the zone's story?
- Political climate: Accurate to the game?
- Phase states: Real phased content?
- Connected zones: Match actual in-game connections?

### 2. NPCs (0-4)

- Are these real NPCs from the zone?
- Personality and role fields — meaningful or generic filler?
- Relationships — do they reference real NPCs?
- Quest threads — real quest connections?
- Coverage — did it find the important NPCs or just a few?

### 3. Factions (0-4)

- Real in-game factions present in this zone?
- Inter-faction relations accurate?
- Ideology and goals — meaningful or generic?
- Coverage — major factions represented?

### 4. Lore (0-4)

- Real historical/mythological lore for this zone?
- Content depth — substantial or surface-level?
- Categories appropriate (history, mythology, etc.)?
- Era accuracy?

### 5. Narrative Items (0-4)

- Real notable items from this zone?
- Story arcs and wielder lineage accurate?
- Significance ratings appropriate?

### 6. Source Quality (0-4)

- Tier distribution: mostly official/primary, or tertiary junk?
- Domain diversity: multiple authoritative sources?
- Any hallucinated URLs?

### 7. Cross-Reference (0-4)

- Did it run?
- Confidence scores — reasonable for the data quality?
- Conflicts identified — real issues or false positives?

### 8. Discovery (0-4)

- Connected zones are real and adjacent in-game?
- Coverage — found the major connections?
- No hallucinated zone names?

---

## Summary

| Category | Score | Notes |
|----------|-------|-------|
| Zone Data | /4 | |
| NPCs | /4 | |
| Factions | /4 | |
| Lore | /4 | |
| Narrative Items | /4 | |
| Source Quality | /4 | |
| Cross-Reference | /4 | |
| Discovery | /4 | |
| **Total** | **/32** | |

## Prompt Tuning Notes

_What needs to change in orchestrator/worker prompts based on this run:_

-
-
-
