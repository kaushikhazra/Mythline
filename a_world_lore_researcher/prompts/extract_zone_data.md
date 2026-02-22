Extract all structured lore data for the zone '{zone_name}' from the raw content below.

The content is organized into labeled sections. Extract data from each section into the corresponding output field:

### ZONE OVERVIEW -> `zone` field
- name: Zone name
- level_range: min and max level (integers)
- narrative_arc: The zone's overall story arc
- political_climate: Current political situation
- access_gating: Requirements to enter the zone
- phase_states: Named world phases with descriptions
- connected_zones: Adjacent zones (slugified names, e.g. "westfall")
- era: The WoW expansion or era this data applies to

### NPCs AND NOTABLE CHARACTERS -> `npcs` array
For each NPC found:
- name: NPC name
- personality: Personality description
- motivations: List of character motivations
- relationships: Relations to other NPCs (name, type, description)
- quest_threads: Quest chains they participate in
- phased_state: If phased, which phase they appear in
- role: Their role (quest giver, vendor, boss, etc.)

### FACTIONS AND ORGANIZATIONS -> `factions` array
For each faction found:
- name: Faction name
- level: Faction tier (major, minor, subfaction)
- inter_faction: Relations with other factions (name, stance, description)
- exclusive_with: Mutually exclusive faction names
- ideology: Core beliefs and values
- goals: List of faction objectives

### LORE, HISTORY, AND MYTHOLOGY -> `lore` array
For each lore entry found:
- title: Lore topic title
- category: One of: history, mythology, cosmology, prophecy, legend
- content: The lore content summary
- era: Time period or expansion

### LEGENDARY ITEMS AND NARRATIVE OBJECTS -> `narrative_items` array
For each item found:
- name: Item name
- story_arc: The story surrounding this item
- wielder_lineage: List of known wielders in order
- power_description: What the item does
- significance: One of: legendary, epic, notable

Extract as many entries as the content supports. Do not invent data not present in the source material. If a section has no relevant content, return an empty array for that field.

Sources used (prefer higher-tier sources for conflicts):
{source_info}

--- RAW CONTENT ---

{raw_content}
