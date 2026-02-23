# WLR Research Depth Fix — Design

## Decisions Log

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Two-phase research via richer RESEARCH_TOPICS instructions, not new pipeline steps | Preserves the 9-step checkpoint structure. The agent already has autonomy to make multiple search+crawl calls within one step. (RD-1, RD-2) |
| D2 | Crawl cache on LoreResearcher class, not checkpoint or ResearchContext | In-memory per-zone cache avoids bloating checkpoint serialization. Accessible from crawl_webpage tool via closure. Reset per zone. (RD-6) |
| D3 | Per-category extraction agents pre-created in __init__, data-driven via EXTRACTION_CATEGORIES dict | Clean, extensible pattern. Each category gets its own output_type, prompt, and token budget share. (RD-3) |
| D4 | Hybrid confidence scoring: LLM for semantic cross-references, Python for mechanical field caps | LLM is good at "Defias is mentioned in narrative_arc but missing from factions." Python is cheaper and deterministic for ">50% empty personality." (RD-5) |
| D5 | Quality warnings computed in Python and added to ResearchPackage, not blocking | Honest metadata for the validator. Non-blocking so partial packages still flow. (RD-7) |
| D6 | extract_zone_data.md replaced by 5 per-category prompt files | Category-specific prompts enable deeper, more targeted extraction instructions per domain. (RD-3) |
| D7 | Token budget split: NPCs 30%, Factions 25%, Lore 25%, Zone 10%, Items 10% | NPCs have the most entities and fields. Zone and items are structurally simpler. Proportional to data complexity. (RD-3) |

---

## 1. Research Prompt Redesign (RD-1, RD-2)

### 1.1 research_zone.md — Rewritten

The current prompt is 3 lines and says "search, crawl, focus on wikis." The new prompt adds explicit two-phase instructions and the requirement to cover both friendly and hostile entities.

```markdown
Research the zone '{zone_name}' using your web search and crawl tools.

## Research Strategy

### Phase 1: Discover
1. Search for overview and category pages about the topic.
2. Crawl the top results to get a broad picture.
3. From the crawled content, identify specific entity NAMES (NPCs, factions, items, events).

### Phase 2: Deep Dive
4. For each important entity name discovered in Phase 1, search for and crawl its
   INDIVIDUAL wiki page (e.g., search for "Edwin VanCleef warcraft wiki" and crawl
   the dedicated page, not just the zone overview that mentions the name).
5. Prioritize individual pages for: major NPCs (10-15 most important), all named
   factions, dungeon/raid bosses, and key lore figures.

### Source Priority
- Prefer official wikis (wowpedia.fandom.com) and primary databases (warcraft.wiki.gg).
- Use wowhead.com for structured NPC/quest data.
- Avoid re-crawling URLs you have already visited — if you already have a page's content, move on to new pages.

{instructions}
```

### 1.2 RESEARCH_TOPICS — Rewritten

These are the `instructions` parameter passed to `research_zone()` and inserted into the `{instructions}` slot. Each topic now has explicit two-phase instructions and hostile/antagonist coverage.

```python
RESEARCH_TOPICS = {
    "zone_overview_research": (
        "Focus on zone overview for {zone} in {game}.\n\n"
        "Phase 1 — Search for the zone's main wiki page and overview articles. "
        "Extract: level range, expansion era, narrative arc (the FULL story — "
        "political backstory, primary conflict, factional tensions, and resolution, "
        "not just a one-sentence summary), political climate (governing factions, "
        "neglected populations, power struggles), access gating, phase states "
        "(Cataclysm changes, quest progression phases), sub-areas and landmarks.\n\n"
        "Phase 2 — If the zone has a major storyline or dungeon, search for and crawl "
        "the dedicated wiki page for that storyline or dungeon (e.g., 'The Deadmines' "
        "page, not just the zone page that mentions it)."
    ),
    "npc_research": (
        "Focus on NPCs and notable characters in {zone} in {game}.\n\n"
        "Phase 1 — Search for NPC lists, zone quest givers, and notable characters. "
        "Crawl category/overview pages to discover NPC NAMES.\n\n"
        "Phase 2 — For the 10-15 most important NPCs discovered, search for and crawl "
        "each NPC's INDIVIDUAL wiki page. Extract from each page: personality, "
        "motivations, relationships to other NPCs, role (quest giver, vendor, boss, "
        "antagonist, faction leader), quest chains, phased/expansion appearances.\n\n"
        "CRITICAL: Search for BOTH friendly and hostile NPCs:\n"
        "- Quest givers, vendors, flight masters, innkeepers\n"
        "- Dungeon bosses and raid bosses associated with this zone\n"
        "- Antagonist leaders and villain NPCs\n"
        "- Faction leaders (both allied and enemy)\n"
        "Do NOT stop at quest-giver lists. Explicitly search for "
        "'{zone} bosses', '{zone} antagonists', and '{zone} dungeon bosses'."
    ),
    "faction_research": (
        "Focus on factions and organizations in {zone} in {game}.\n\n"
        "Phase 1 — Search for factions active in this zone. Crawl overview pages "
        "to discover faction NAMES.\n\n"
        "Phase 2 — For EVERY named faction discovered, search for and crawl the "
        "faction's INDIVIDUAL wiki page. Extract: ideology, core beliefs, origin "
        "story (how and why the faction formed), goals, key members and leaders, "
        "inter-faction relationships (allied, hostile, neutral — name the specific "
        "factions), hierarchy (parent factions, sub-factions), mutual exclusions.\n\n"
        "CRITICAL: Search for BOTH friendly and hostile factions:\n"
        "- Allied organizations and militia groups\n"
        "- Antagonist factions, criminal organizations, hostile forces\n"
        "- Governing authorities and their local presence\n"
        "Do NOT stop at allied faction pages. Explicitly search for "
        "'{zone} enemy factions', '{zone} hostile organizations'."
    ),
    "lore_research": (
        "Focus on lore, history, mythology, and cosmology of {zone} in {game}.\n\n"
        "Phase 1 — Search for the zone's lore and history articles. Crawl overview "
        "pages to identify major lore EVENTS and FIGURES.\n\n"
        "Phase 2 — For each major lore event or figure, search for and crawl its "
        "INDIVIDUAL wiki page. Extract: what happened, WHY it happened (causes), "
        "what it caused (consequences), named actors involved, era/timeline placement.\n\n"
        "Prioritize causal chains: the sequence of events that created the zone's "
        "current state. Include origin stories for major factions and conflicts."
    ),
    "narrative_items_research": (
        "Focus on narrative items and artifacts in {zone} in {game}.\n\n"
        "Search for legendary items, quest items with story significance, "
        "dungeon loot with narrative context, and artifacts tied to the zone's lore.\n\n"
        "Extract: story arc, wielder lineage, power description, significance tier.\n\n"
        "ONLY include items with genuine narrative significance — NOT crafting recipes, "
        "cooking items, vendor trash, or generic consumables. If the zone has no "
        "truly significant narrative items, that is acceptable — an empty result "
        "is better than padding with irrelevant items."
    ),
}
```

---

## 2. URL Deduplication (RD-6)

### 2.1 Crawl Cache on LoreResearcher

A `dict[str, str]` keyed by normalized URL, storing full crawled content. Lives on the `LoreResearcher` instance (in-memory, not checkpointed). Accessible from the `crawl_webpage` tool via Python closure.

**Note:** The cache is best-effort — lost on process restart. If the daemon crashes mid-pipeline and resumes, URLs from earlier steps may be re-crawled. This is acceptable: the cache is a performance optimization, not a correctness requirement, and the primary dedup benefit (within a single continuous run) is preserved.

```python
# In LoreResearcher.__init__
self._crawl_cache: dict[str, str] = {}

# New method (replaces reset_zone_tokens)
def reset_zone_state(self) -> None:
    """Reset per-zone state: token counter and crawl cache."""
    self._zone_tokens = 0
    self._crawl_cache.clear()
```

### 2.2 URL Normalization Helper

```python
def _normalize_url(url: str) -> str:
    """Normalize a URL for cache dedup: strip trailing slashes and fragments."""
    return url.rstrip("/").split("#")[0]
```

### 2.3 Updated crawl_webpage Tool

```python
@self._research_agent.tool
async def crawl_webpage(
    ctx: RunContext[ResearchContext], url: str
) -> str:
    """Crawl a URL and extract its full content as markdown."""
    # Normalize URL for dedup (strip trailing slashes and fragments)
    cache_key = _normalize_url(url)

    # URL dedup: return cached content if already crawled this zone
    if cache_key in self._crawl_cache:
        content = self._crawl_cache[cache_key]
        ctx.deps.raw_content.append(content)
        ctx.deps.sources.append(_make_source_ref(url))
        truncated = content[:CRAWL_CONTENT_TRUNCATE_CHARS]
        if len(content) > CRAWL_CONTENT_TRUNCATE_CHARS:
            return truncated + "\n\n[... cached, full version captured ...]"
        return content

    result = await rest_crawl_url(url)
    content = result.get("content")
    if content:
        self._crawl_cache[cache_key] = content  # Cache for future steps
        ctx.deps.raw_content.append(content)
        ctx.deps.sources.append(_make_source_ref(url))
        if len(content) > CRAWL_CONTENT_TRUNCATE_CHARS:
            return content[:CRAWL_CONTENT_TRUNCATE_CHARS] + "\n\n[... content truncated, full version captured ...]"
        return content
    error = result.get("error", "unknown error")
    return f"Failed to crawl {url}: {error}"
```

### 2.4 Pipeline Integration

In `daemon.py` (or wherever `researcher.reset_zone_tokens()` is called), replace with `researcher.reset_zone_state()` to also clear the crawl cache at the start of each zone.

---

## 3. Richer Summarization Schema Hints (RD-4)

Replace the generic `TOPIC_SCHEMA_HINTS` in `pipeline.py` with depth-preserving hints that use explicit "MUST PRESERVE" directives and proper noun retention.

```python
TOPIC_SCHEMA_HINTS = {
    "zone_overview_research": (
        "zone metadata: name, level range, expansion era. "
        "MUST PRESERVE: narrative arc (full storyline — political backstory, "
        "primary conflict, factional tensions, and resolution — not a tagline), "
        "political climate (governing factions, neglected populations, power "
        "struggles), phase states (Cataclysm changes, quest progression phases), "
        "sub-areas and landmarks. "
        "Preserve ALL proper nouns (NPC names, faction names, place names) "
        "even when compressing surrounding text."
    ),
    "npc_research": (
        "NPCs: names, titles, faction allegiance. "
        "MUST PRESERVE per NPC: personality traits and demeanor, motivations "
        "and goals, relationships to other NPCs (allies, rivals, family, mentors), "
        "role classification (quest giver, vendor, boss, antagonist, faction leader), "
        "quest chains they give or participate in, phased/expansion appearances. "
        "Include BOTH friendly and hostile NPCs — quest givers AND dungeon bosses, "
        "antagonist leaders, faction leaders. "
        "Preserve ALL NPC proper names even when compressing other text."
    ),
    "faction_research": (
        "factions: names, type (major faction, guild, cult, military). "
        "MUST PRESERVE: ideology and core beliefs, stated goals, "
        "origin story (how and why the faction formed), key members and leaders, "
        "inter-faction relationships (allied/hostile/neutral — name specific factions), "
        "mutual exclusions, hierarchy (parent factions, sub-factions). "
        "Include BOTH friendly and hostile factions — allied organizations AND "
        "antagonist groups, criminal organizations, hostile forces. "
        "Preserve ALL faction and leader proper names."
    ),
    "lore_research": (
        "lore: event titles, era/timeline placement. "
        "MUST PRESERVE: major historical events with causal chains (what happened, "
        "why it happened, what it caused), named actors in each event, "
        "mythology and cosmological rules, power sources and their origins. "
        "Preserve chronological ordering and cause-effect relationships. "
        "Keep ALL proper nouns (people, places, artifacts, faction names)."
    ),
    "narrative_items_research": (
        "items and artifacts: names, significance tier (legendary, epic, quest, notable). "
        "MUST PRESERVE: story arc (how the item fits into the zone's narrative), "
        "wielder lineage, power description, quest relevance. "
        "EXCLUDE crafting recipes, cooking items, vendor trash, generic consumables. "
        "An empty result is better than irrelevant items."
    ),
}
```

---

## 4. Per-Category Extraction Pipeline (RD-3)

### 4.1 Per-Category Output Models

New models in `agent.py`. Zone uses `ZoneData` directly. Others need wrapper models for Pydantic AI `output_type`.

```python
class NPCExtractionResult(BaseModel):
    npcs: list[NPCData] = Field(default_factory=list)

class FactionExtractionResult(BaseModel):
    factions: list[FactionData] = Field(default_factory=list)

class LoreExtractionResult(BaseModel):
    lore: list[LoreData] = Field(default_factory=list)

class NarrativeItemExtractionResult(BaseModel):
    narrative_items: list[NarrativeItemData] = Field(default_factory=list)
```

### 4.2 Extraction Categories Config

Data-driven mapping in `agent.py`:

```python
EXTRACTION_CATEGORIES: dict[str, tuple[type[BaseModel], str, float]] = {
    "zone": (ZoneData, "extract_zone", 0.10),
    "npcs": (NPCExtractionResult, "extract_npcs", 0.30),
    "factions": (FactionExtractionResult, "extract_factions", 0.25),
    "lore": (LoreExtractionResult, "extract_lore", 0.25),
    "narrative_items": (NarrativeItemExtractionResult, "extract_narrative_items", 0.10),
}
```

### 4.3 Pre-Created Extraction Agents

In `LoreResearcher.__init__`, replace the single `_extraction_agent` with per-category agents:

```python
# Replace: self._extraction_agent = Agent(LLM_MODEL, ..., output_type=ZoneExtraction)
# With:
self._extraction_agents: dict[str, Agent] = {}
for category, (output_type, _, _) in EXTRACTION_CATEGORIES.items():
    self._extraction_agents[category] = Agent(
        LLM_MODEL,
        system_prompt=load_prompt(__file__, "system_prompt"),
        output_type=output_type,
        retries=2,
    )
```

### 4.4 Generic extract_category() Method

Replaces `extract_zone_data()`:

```python
async def extract_category[T: BaseModel](
    self,
    category: str,
    zone_name: str,
    content: str,
    sources: list[SourceReference],
) -> T:
    """Extract structured data for one category from summarized content.

    Returns the output_type associated with this category in EXTRACTION_CATEGORIES.
    The generic return type enables type-safe access at call sites via cast().
    """
    _, prompt_name, token_share = EXTRACTION_CATEGORIES[category]
    agent = self._extraction_agents[category]

    source_info = "\n".join(
        f"- {s.url} (tier: {s.tier.value})" for s in sources
    )
    template = load_prompt(__file__, prompt_name)
    prompt = template.format(
        zone_name=zone_name,
        source_info=source_info,
        raw_content=content,
    )

    budget = int(PER_ZONE_TOKEN_BUDGET * token_share)
    result = await agent.run(
        prompt,
        usage_limits=UsageLimits(response_tokens_limit=budget),
    )
    self._zone_tokens += result.usage().total_tokens or 0
    return result.output
```

### 4.5 Per-Category Prompt Templates

Five new prompt files replace the single `extract_zone_data.md`. Each receives `{zone_name}`, `{source_info}`, and `{raw_content}`.

**`prompts/extract_zone.md`**:
```markdown
Extract structured zone metadata for '{zone_name}' from the content below.

Output a single zone record with:
- name: Zone name
- level_range: min and max level (integers)
- narrative_arc: The zone's FULL story arc — not a tagline. Include: primary conflict,
  political backstory, key factions involved, resolution or current state. Minimum 200 characters.
- political_climate: Who governs, who is neglected, what tensions exist
- access_gating: Requirements to enter the zone (empty list if none)
- phase_states: Named world phases with descriptions and triggers (Cataclysm changes, etc.)
- connected_zones: Adjacent zones (slugified, e.g. "elwynn-forest")
- era: The WoW expansion(s) this data covers (note if zone was reworked across expansions)

Do not invent data. If a field has no supporting content, leave it at its default value.

Sources (prefer higher-tier for conflicts):
{source_info}

--- RAW CONTENT ---

{raw_content}
```

**`prompts/extract_npcs.md`**:
```markdown
Extract all NPCs and notable characters for the zone '{zone_name}' from the content below.

For EACH NPC found, extract:
- name: NPC name
- personality: Personality description — demeanor, temperament, notable traits
- motivations: List of what drives this character
- relationships: Relations to other NPCs — [{npc_id, type (ally/rival/family/mentor/subordinate), description}]
- quest_threads: Quest chains they give or participate in
- phased_state: If phased, which expansion/phase they appear in
- role: Their function — one of: quest_giver, vendor, flight_master, innkeeper, boss, antagonist, faction_leader, trainer, guard, civilian

Include BOTH friendly and hostile NPCs:
- Quest givers, vendors, trainers
- Dungeon and raid bosses
- Antagonist leaders, villain NPCs
- Faction leaders (allied and enemy)

Extract as many NPCs as the content supports. Do not invent data not present in the source material.
If personality or motivation data is not available for an NPC, leave those fields empty rather than guessing.

Sources (prefer higher-tier for conflicts):
{source_info}

--- RAW CONTENT ---

{raw_content}
```

**`prompts/extract_factions.md`**:
```markdown
Extract all factions and organizations active in the zone '{zone_name}' from the content below.

For EACH faction found, extract:
- name: Faction name
- level: Tier — one of: major_faction, guild, order, cult, military, criminal, tribal
- inter_faction: Relations with other factions — [{faction_id, stance (allied/hostile/neutral), description}]
- exclusive_with: Mutually exclusive faction names
- ideology: Core beliefs, values, and worldview
- goals: List of faction objectives

Include BOTH friendly and hostile factions:
- Allied militias, guilds, governing bodies
- Antagonist organizations, criminal brotherhoods, hostile forces
- Any faction mentioned in the zone's narrative arc

Extract as many factions as the content supports. Do not invent data.

Sources (prefer higher-tier for conflicts):
{source_info}

--- RAW CONTENT ---

{raw_content}
```

**`prompts/extract_lore.md`**:
```markdown
Extract lore entries for the zone '{zone_name}' from the content below.

For EACH distinct lore topic, create an entry with:
- title: Lore topic title (e.g., "The Stonemasons' Betrayal", "Rise of the Defias Brotherhood")
- category: One of: history, mythology, cosmology, power_source
- content: The lore content — include causal chains (what happened → why → consequences),
  named actors, and timeline placement. This should be a substantive summary, not a tagline.
- era: Time period or expansion this lore pertains to

Prioritize:
- Origin stories for the zone's major factions and conflicts
- Key historical events that shaped the zone's current state
- Dungeon/raid lore and boss backstories
- Character origin stories for major NPCs

Extract as many distinct lore entries as the content supports. Do not merge unrelated events.

Sources (prefer higher-tier for conflicts):
{source_info}

--- RAW CONTENT ---

{raw_content}
```

**`prompts/extract_narrative_items.md`**:
```markdown
Extract narrative items and artifacts for the zone '{zone_name}' from the content below.

For EACH item with genuine narrative significance, extract:
- name: Item name
- story_arc: How this item fits into the zone's story
- wielder_lineage: List of known wielders or owners in order
- power_description: What the item does or represents
- significance: One of: legendary, epic, quest, notable

ONLY include items that serve the narrative:
- Legendary weapons or artifacts tied to lore figures
- Quest items that reveal plot (documents, plans, keys to storylines)
- Dungeon loot with narrative backstory
- Symbolic items central to the zone's themes

Do NOT include: crafting recipes, cooking items, vendor trash, generic consumables, profession materials.
If the zone has no truly significant narrative items, return an empty list.

Sources (prefer higher-tier for conflicts):
{source_info}

--- RAW CONTENT ---

{raw_content}
```

### 4.6 Updated step_extract_all in pipeline.py

The step remains one pipeline step but internally runs 5 extraction passes. Extraction sub-passes are **not individually checkpointed** — a failure in any pass requires re-running all 5. This is acceptable because extraction calls are lightweight (~seconds each) compared to research and summarization (~minutes each):

```python
async def step_extract_all(
    checkpoint: ResearchCheckpoint,
    researcher: LoreResearcher,
    publish_fn: Callable | None = None,
) -> ResearchCheckpoint:
    zone_name = checkpoint.zone_name
    raw_blocks = checkpoint.step_data.get("research_raw_content", [])
    source_dicts = checkpoint.step_data.get("research_sources", [])
    sources = [SourceReference(**sd) for sd in source_dicts]

    # Reconstruct and summarize (unchanged)
    sections = _reconstruct_labeled_content(raw_blocks)
    summarized = await _maybe_summarize_sections(sections)

    # Build topic -> summarized content map
    section_content: dict[str, str] = {}
    for (topic, _, _), content in zip(sections, summarized):
        section_content[topic] = content

    # Per-category extraction (cast() for type safety — actual type
    # is determined by EXTRACTION_CATEGORIES output_type for each key)
    zone_data = cast(ZoneData, await researcher.extract_category(
        "zone", zone_name,
        section_content.get("zone_overview_research", ""), sources,
    ))
    npcs_result = cast(NPCExtractionResult, await researcher.extract_category(
        "npcs", zone_name,
        section_content.get("npc_research", ""), sources,
    ))
    factions_result = cast(FactionExtractionResult, await researcher.extract_category(
        "factions", zone_name,
        section_content.get("faction_research", ""), sources,
    ))
    lore_result = cast(LoreExtractionResult, await researcher.extract_category(
        "lore", zone_name,
        section_content.get("lore_research", ""), sources,
    ))
    items_result = cast(NarrativeItemExtractionResult, await researcher.extract_category(
        "narrative_items", zone_name,
        section_content.get("narrative_items_research", ""), sources,
    ))

    # Assemble ZoneExtraction from per-category results
    extraction = ZoneExtraction(
        zone=zone_data,
        npcs=npcs_result.npcs,
        factions=factions_result.factions,
        lore=lore_result.lore,
        narrative_items=items_result.narrative_items,
    )
    checkpoint.step_data["extraction"] = extraction.model_dump(mode="json")
    return checkpoint
```

---

## 5. Completeness-Aware Confidence Scoring (RD-5)

### 5.1 Updated cross_reference.md (System Prompt)

```markdown
You are a lore consistency and completeness validator. Your job is to examine
extracted game lore data and identify:

1. **Contradictions** — conflicting information between sources
2. **Cross-category gaps** — entities mentioned in one category but missing from another

### Contradiction Detection
For each conflict found, identify:
- The data point in question
- The two conflicting claims and their sources
- A suggested resolution (prefer official/primary sources)

### Cross-Category Gap Detection
Check for:
- Faction names mentioned in zone.narrative_arc or zone.political_climate that do NOT
  appear in the factions list → note as a gap
- NPC names mentioned in another NPC's quest_threads or relationships that do NOT
  appear in the npcs list → note as a gap
- Lore events that reference factions or NPCs not present in their respective lists → note

### Confidence Scoring
Assign confidence scores (0.0 to 1.0) for each category using this rubric:
- 0.9-1.0: Multiple sources agree AND all key fields populated AND no cross-category gaps
- 0.7-0.8: Good source coverage AND most fields populated
- 0.5-0.6: Source coverage adequate BUT significant empty fields or cross-category gaps
- 0.3-0.4: Major gaps — missing factions mentioned in narrative, most NPC fields empty
- 0.0-0.2: Minimal extraction — barely any usable data

Important: A category with many entities but all-empty depth fields (e.g., 10 NPCs with
no personality data) should score LOW (0.3-0.4), not high.
```

### 5.2 Updated cross_reference_task.md (User Prompt)

```markdown
Cross-reference the following extracted lore data for consistency and completeness.

Zone: {zone_name}
NPCs: {npc_count}
Factions: {faction_count}
Lore entries: {lore_count}
Narrative items: {narrative_item_count}

Check specifically:
1. Are there faction names in the zone's narrative_arc or political_climate that are NOT
   in the factions list? If so, list them as cross-category gaps.
2. Are there NPC names in quest_threads or relationships that are NOT in the npcs list?
3. What percentage of NPCs have empty personality fields? Empty role fields?
4. Are any contradictions present between data points?

Assign confidence scores per category using the completeness-weighted rubric.
Use these exact category keys: `zone`, `npcs`, `factions`, `lore`, `narrative_items`.

Full data:
{full_data}
```

### 5.3 Python Confidence Caps

Applied AFTER the LLM cross-reference, in `step_cross_reference` or as a helper called from it. Deterministic mechanical adjustments:

```python
def _apply_confidence_caps(
    extraction: ZoneExtraction,
    confidence: dict[str, float],
) -> dict[str, float]:
    """Apply mechanical confidence caps based on field completeness."""
    capped = dict(confidence)

    # Zero-entity caps: if a category extracted nothing, cap low
    if not extraction.npcs:
        capped["npcs"] = min(capped.get("npcs", 0.0), 0.2)
    else:
        total = len(extraction.npcs)
        empty_personality = sum(1 for n in extraction.npcs if not n.personality)
        empty_role = sum(1 for n in extraction.npcs if not n.role)

        if empty_personality / total > 0.5:
            capped["npcs"] = min(capped.get("npcs", 0.0), 0.4)
        if empty_role / total > 0.5:
            capped["npcs"] = min(capped.get("npcs", 0.0), 0.4)

    if not extraction.factions:
        capped["factions"] = min(capped.get("factions", 0.0), 0.2)

    return capped
```

Called from `step_cross_reference`:
```python
async def step_cross_reference(checkpoint, researcher, publish_fn=None):
    extraction_dict = checkpoint.step_data.get("extraction", {})
    extraction = ZoneExtraction.model_validate(extraction_dict)

    cr_result = await researcher.cross_reference(extraction)

    # Apply mechanical confidence caps
    cr_result.confidence = _apply_confidence_caps(extraction, cr_result.confidence)

    checkpoint.step_data["cross_reference"] = cr_result.model_dump(mode="json")
    return checkpoint
```

---

## 6. Quality Thresholds (RD-7)

### 6.1 Model Change

Add `quality_warnings` to `ResearchPackage` in `models.py`:

```python
class ResearchPackage(BaseModel):
    zone_name: str
    zone_data: ZoneData
    npcs: list[NPCData] = Field(default_factory=list)
    factions: list[FactionData] = Field(default_factory=list)
    lore: list[LoreData] = Field(default_factory=list)
    narrative_items: list[NarrativeItemData] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    confidence: dict[str, float] = Field(default_factory=dict)
    conflicts: list[Conflict] = Field(default_factory=list)
    quality_warnings: list[str] = Field(default_factory=list)  # NEW
```

### 6.2 Quality Warning Logic

Python function in `pipeline.py`, called from `step_package_and_send`:

```python
def _compute_quality_warnings(extraction: ZoneExtraction) -> list[str]:
    """Compute quality warnings based on content thresholds."""
    warnings: list[str] = []

    # Shallow narrative arc
    if len(extraction.zone.narrative_arc) < 200:
        warnings.append("shallow_narrative_arc")

    # No NPC personality data
    if extraction.npcs and all(not n.personality for n in extraction.npcs):
        warnings.append("no_npc_personality_data")

    # Missing antagonists (heuristic: check for boss/antagonist roles + hostile factions)
    has_antagonist_npc = any(
        n.role and any(
            keyword in n.role.lower()
            for keyword in ("boss", "antagonist", "villain")
        )
        for n in extraction.npcs
    )
    has_hostile_faction = any(
        any(r.stance == FactionStance.HOSTILE for r in f.inter_faction)
        for f in extraction.factions
    )
    zone_mentions_dungeon = any(
        keyword in extraction.zone.narrative_arc.lower()
        for keyword in ("dungeon", "raid", "instance", "mine", "mines")
    ) or any(
        keyword in entry.content.lower()
        for entry in extraction.lore
        for keyword in ("dungeon", "raid", "instance")
    )

    if zone_mentions_dungeon and not has_antagonist_npc and not has_hostile_faction:
        warnings.append("missing_antagonists")

    return warnings
```

### 6.3 Integration in step_package_and_send

```python
async def step_package_and_send(checkpoint, researcher, publish_fn=None):
    # ... existing code to rebuild extraction and cr_result ...

    warnings = _compute_quality_warnings(extraction)

    package = ResearchPackage(
        zone_name=zone_name,
        zone_data=extraction.zone,
        npcs=extraction.npcs,
        factions=extraction.factions,
        lore=extraction.lore,
        narrative_items=extraction.narrative_items,
        sources=all_sources,
        confidence=cr_result.confidence,
        conflicts=cr_result.conflicts,
        quality_warnings=warnings,  # NEW
    )
    # ... rest unchanged ...
```

---

## Files Changed

| File | Change | Req |
|------|--------|-----|
| `prompts/research_zone.md` | Rewrite: add two-phase research strategy, source priority, dedup hint | RD-1, RD-2 |
| `src/pipeline.py` — `RESEARCH_TOPICS` | Rewrite all 5 topic strings: two-phase instructions, antagonist/hostile emphasis | RD-1, RD-2 |
| `src/pipeline.py` — `TOPIC_SCHEMA_HINTS` | Rewrite all 5 hint strings: MUST PRESERVE directives, proper noun retention | RD-4 |
| `src/pipeline.py` — `step_extract_all()` | Refactor: 5 sequential `extract_category()` calls, assemble `ZoneExtraction` | RD-3 |
| `src/pipeline.py` — `step_cross_reference()` | Add `_apply_confidence_caps()` call after LLM cross-reference | RD-5 |
| `src/pipeline.py` — `step_package_and_send()` | Add `_compute_quality_warnings()` call, pass to `ResearchPackage` | RD-7 |
| `src/pipeline.py` — new functions | `_apply_confidence_caps()`, `_compute_quality_warnings()` | RD-5, RD-7 |
| `src/pipeline.py` — imports | Add `cast` from `typing`, `FactionStance` from `src.models`, extraction result models from `src.agent` | RD-3, RD-5, RD-7 |
| `src/agent.py` — `LoreResearcher.__init__` | Add `_crawl_cache` dict; replace `_extraction_agent` with per-category `_extraction_agents` dict | RD-3, RD-6 |
| `src/agent.py` — `crawl_webpage` tool | Add URL normalization + cache check before `rest_crawl_url()`, cache content on hit | RD-6 |
| `src/agent.py` — `_normalize_url()` | New helper: strip trailing slashes and fragments for cache dedup | RD-6 |
| `src/agent.py` — `reset_zone_tokens()` | Rename to `reset_zone_state()`, also clears `_crawl_cache` | RD-6 |
| `src/agent.py` — `extract_zone_data()` | Replace with generic `extract_category()` method | RD-3 |
| `src/agent.py` — new models | `NPCExtractionResult`, `FactionExtractionResult`, `LoreExtractionResult`, `NarrativeItemExtractionResult`, `EXTRACTION_CATEGORIES` dict | RD-3 |
| `src/models.py` — `ResearchPackage` | Add `quality_warnings: list[str]` field | RD-7 |
| `prompts/extract_zone_data.md` | Delete (replaced by per-category prompts) | RD-3 |
| `prompts/extract_zone.md` | New — zone metadata extraction prompt | RD-3 |
| `prompts/extract_npcs.md` | New — NPC extraction with personality/role emphasis | RD-3 |
| `prompts/extract_factions.md` | New — faction extraction with ideology/origin emphasis | RD-3 |
| `prompts/extract_lore.md` | New — lore extraction with causal chain emphasis | RD-3 |
| `prompts/extract_narrative_items.md` | New — items extraction with significance filtering | RD-3 |
| `prompts/cross_reference.md` | Rewrite: add completeness checks, updated confidence rubric | RD-5 |
| `prompts/cross_reference_task.md` | Rewrite: add cross-category gap detection instructions | RD-5 |
| `src/daemon.py` | Update `reset_zone_tokens()` call to `reset_zone_state()` | RD-6 |

---

## Future Work (Out of Scope)

- **Parallel per-category extraction** — The 5 extraction calls are sequential. They could run concurrently via `asyncio.gather()` for speed. Deferred because sequential is simpler to debug and token accounting is easier.
- **Adaptive token budget per category** — Currently fixed shares (NPCs 30%, etc.). A future pass could allocate more tokens to categories with richer raw content.
- **Cross-zone entity deduplication** — NPCs and factions that appear in multiple zones should be merged, not duplicated. This is a validator concern, not a researcher concern.
- **Wowhead.com structured data integration** — Wowhead has structured NPC/quest databases that could supplement wiki prose. Requires specific crawl patterns.
