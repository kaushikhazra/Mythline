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
