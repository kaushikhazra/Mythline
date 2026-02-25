Extract all NPCs and notable characters for the zone '{zone_name}' from the content below.

For EACH NPC found, extract:
- name: NPC name
- personality: Personality description — demeanor, temperament, notable traits
- motivations: List of what drives this character
- relationships: Relations to other NPCs — [{{npc_id, type (ally/rival/family/mentor/subordinate), description}}]
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
