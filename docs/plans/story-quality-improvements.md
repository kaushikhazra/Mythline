# Story Quality Improvements Plan

This plan addresses gaps identified in the story creation pipeline. Issues are categorized by root cause and prioritized for incremental implementation alongside ongoing story production.

## Problem Summary

| Category | Issue Type | Frequency | Impact |
|----------|-----------|-----------|--------|
| System/Data | Web scraping failures | Common | High |
| System/Data | Missing/inconsistent formatting | Common | Low |
| LLM Retrieval | Zone/location confusion | Occasional | High |
| LLM Retrieval | Lore conflation (wrong sources) | Occasional | High |
| LLM Inherent | Creative embellishment drift | Always | Medium |

---

## Phase 1: Validation & Post-Processing (Quick Wins)

### 1.1 Output Schema Validation
**Problem:** Actor names inconsistent ("Runewarden" vs "Deryan"), missing coordinates, formatting issues.

**Solution:** Add Pydantic validators to output models.

**Files to modify:**
- `src/graphs/shot_creator_graph/models/output_models.py`
- `src/graphs/story_research_graph/models/research_models.py`

**Validators to add:**
- [ ] Actor name normalization (strip titles, use first name for dialogue)
- [ ] Coordinate validation (warn if null for key locations)
- [ ] Text capitalization check (sentences start uppercase)
- [ ] Title sanitization (no underscores, proper spacing)

### 1.2 Post-Processing Pass
**Problem:** Minor formatting issues slip through.

**Solution:** Add cleanup function after JSON generation.

**Cleanup rules:**
- [ ] Replace underscores in titles with spaces
- [ ] Ensure all `text` fields start with uppercase
- [ ] Normalize NPC names to consistent format
- [ ] Remove duplicate whitespace

---

## Phase 2: Prompt Constraints (Medium Effort)

### 2.1 Zone Boundary Constraints
**Problem:** LLM confuses nearby zones (Sunwell on Quel'Danas vs Eversong Woods).

**Solution:** Add explicit zone constraints to prompts.

**Files to modify:**
- `src/agents/story_setting_extractor_agent/prompts/system_prompt.md`
- `src/agents/location_extractor_agent/prompts/system_prompt.md`
- `src/agents/shot_creator_agent/prompts/system_prompt.md`

**Prompt additions:**
```markdown
## Zone Constraints
- This story takes place ONLY in: {zone_name}
- DO NOT reference locations outside this zone
- Nearby zones to AVOID mentioning: {excluded_zones}
```

**Zone reference data needed:**
- [ ] Create `data/zones/eversong_woods.json` with boundaries and excluded references
- [ ] Create similar files for other Blood Elf zones

### 2.2 Lore Source Prioritization
**Problem:** LLM retrieves similar-sounding but wrong lore (e.g., druidic runestones vs Blood Elf arcane runestones).

**Solution:** Add faction/race context to extraction prompts.

**Prompt additions:**
```markdown
## Lore Context
- Faction: {faction} (e.g., Blood Elf / Horde)
- Race: {race} (e.g., Blood Elf / Sin'dorei)
- Magic type: {magic_type} (e.g., Arcane, NOT Druidic/Nature)
- Time period: {expansion} (e.g., The Burning Crusade)
```

---

## Phase 3: Vector Storage & RAG (Long-term)

### 3.1 Quest Database from wago.tools
**Problem:** Web scraping is unreliable and slow.

**Solution:** Pre-index quest data from wago.tools DB2 exports.

**Data sources:**
- `https://wago.tools/db2/QuestV2/csv` - Quest definitions
- `https://wago.tools/db2/QuestObjective/csv` - Quest objectives
- `https://wago.tools/db2/Creature/csv` - NPC data
- `https://wago.tools/db2/AreaTable/csv` - Zone information

**Implementation steps:**
- [ ] Create download script for DB2 CSVs
- [ ] Parse and transform to structured JSON
- [ ] Generate embeddings for quest descriptions
- [ ] Store in Qdrant (existing knowledge base infrastructure)

### 3.2 Zone Knowledge Base
**Problem:** Zone descriptions hallucinated or inaccurate.

**Solution:** Pre-authored zone descriptions indexed for retrieval.

**Per-zone data:**
```json
{
  "zone_id": 3430,
  "name": "Eversong Woods",
  "type": "inland_forest",
  "climate": "eternal_autumn",
  "palette": ["gold", "amber", "crimson", "copper"],
  "features": ["golden_leaves", "arcane_spires", "Dead_Scar"],
  "NOT_features": ["coastal", "ocean", "beach", "snow"],
  "adjacent_zones": ["Ghostlands", "Silvermoon City"],
  "faction": "Horde",
  "race": "Blood Elf"
}
```

- [ ] Create zone data files for Blood Elf starting areas
- [ ] Index in knowledge base MCP server
- [ ] Update story_setting_extractor to query zone data first

### 3.3 NPC Knowledge Base
**Problem:** NPC personalities and lore sometimes inaccurate.

**Solution:** Pre-index key NPCs with verified data.

**Per-NPC data:**
```json
{
  "name": "Ranger Sareyn",
  "title": "Ranger",
  "short_name": "Sareyn",
  "faction": "Silvermoon City",
  "race": "Blood Elf",
  "class": "Farstrider",
  "location": "Fairbreeze Village",
  "personality": "Vigilant, commanding, duty-focused",
  "coordinates": {"x": 47.0, "y": 72.0}
}
```

---

## Phase 4: Human Review Integration

### 4.1 Review Checklist Generator
**Problem:** Manual review catches issues but is inconsistent.

**Solution:** Generate a checklist based on known problem areas.

**Checklist items:**
- [ ] Zone name matches throughout
- [ ] No references to wrong zones (Sunwell, Quel'Danas for Eversong stories)
- [ ] NPC names consistent
- [ ] Coordinates present for key locations
- [ ] Magic type matches faction (Arcane for Blood Elves)
- [ ] No browser error artifacts

### 4.2 Diff-Based Review
**Problem:** Hard to spot what changed between research and story.

**Solution:** Generate summary of key facts for quick verification.

**Output:**
```
Zone: Eversong Woods
NPCs: Velan Brightoak, Marniel Amberlight, Ranger Sareyn, Runewarden Deryan
Enemies: Scourge, Wretched, Springpaw Stalkers
Locations: Fairbreeze Village, Dead Scar, Runestone Falithas, Eastern Runestone
```

---

## Implementation Priority

### Immediate (During Next Story)
1. Zone boundary constraints in prompts
2. Actor name normalization

### Next Sprint
3. Post-processing cleanup function
4. Zone reference data files

### Backlog
5. wago.tools DB2 download script
6. Quest knowledge base indexing
7. NPC knowledge base
8. Review checklist generator

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Manual fixes per story | 5-10 | 1-2 |
| Zone confusion errors | Occasional | Rare |
| NPC name inconsistencies | Common | None |
| Scraping failures | Common | Rare (with vector DB) |

---

## Notes

- Each fix should be tested on a new story before moving to next
- Document new issue patterns as they emerge
- Vector storage (Phase 3) eliminates most scraping issues but requires upfront data work
- Human review will always be needed for creative quality - goal is to reduce mechanical errors
