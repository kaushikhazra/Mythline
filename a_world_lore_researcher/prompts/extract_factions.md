Extract all factions and organizations active in the zone '{zone_name}' from the content below.

For EACH faction found, extract:
- name: Faction name
- level: Tier — one of: major_faction, guild, order, cult, military, criminal, tribal
- inter_faction: Relations with other factions. For EACH faction you extract, list its stance
  toward every OTHER faction you extract. Use this exact JSON structure:
  ```json
  [
    {{"faction_id": "Defias Brotherhood", "stance": "hostile", "description": "Sworn enemies — the militia actively hunts Defias operatives"}},
    {{"faction_id": "Kingdom of Stormwind", "stance": "allied", "description": "Reports to the crown and enforces its laws"}}
  ]
  ```
  Valid stance values: allied, hostile, neutral.
  If you extract 3 factions (A, B, C), then A must list its stance toward B and C,
  B must list its stance toward A and C, and C must list its stance toward A and B.
  This is critical — inter-faction dynamics drive the zone's narrative.
- exclusive_with: Mutually exclusive faction names
- ideology: Core beliefs, values, and worldview
- goals: List of faction objectives
- sources: Source references where this faction's data was found (url, domain, tier).
  Every faction must have at least one source.

Include BOTH friendly and hostile factions:
- Allied militias, guilds, governing bodies
- Antagonist organizations, criminal brotherhoods, hostile forces
- Any faction mentioned in the zone's narrative arc

Extract as many factions as the content supports. Do not invent data.

Sources (prefer higher-tier for conflicts):
{source_info}

--- RAW CONTENT ---

{raw_content}
