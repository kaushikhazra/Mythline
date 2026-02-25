Extract all factions and organizations active in the zone '{zone_name}' from the content below.

For EACH faction found, extract:
- name: Faction name
- level: Tier — one of: major_faction, guild, order, cult, military, criminal, tribal
- inter_faction: Relations with other factions — [{{faction_id, stance (allied/hostile/neutral), description}}]
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
