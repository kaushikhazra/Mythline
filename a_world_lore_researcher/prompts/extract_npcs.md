Extract all NPCs and notable characters for the zone '{zone_name}' from the content below.

Each NPC must be a NAMED INDIVIDUAL — a specific person or creature with a proper name.
Examples of valid NPCs: "Marshal Dughan", "Hogger", "Edwin VanCleef", "Brother Sammuel",
"Guard Thomas", "Gramma Stonefield", "Billy Maclure", "Goldtooth".

Exclude creature categories ("Kobolds", "Gnolls"), factions ("Defias Brotherhood"), and
locations ("Northshire Abbey") — these belong in other extraction categories.

For EACH NPC found, extract:
- name: The NPC's individual name
- personality: Personality description — demeanor, temperament, notable traits
- motivations: List of what drives this character
- relationships: Relations to other NPCs — use the NPC's name as npc_id
  (e.g., {{npc_id: "Marshal Dughan", type: "subordinate", description: "Reports to Dughan"}})
- quest_threads: Quest chains they give or participate in. Name the quest if known
  (e.g., ["A Threat Within", "Investigate Echo Ridge"]). Quests are the primary way NPCs
  connect to the zone's narrative — always extract these when available.
- phased_state: If phased, which expansion/phase they appear in
- occupation: Their role or occupation — one of: quest_giver, vendor, flight_master, innkeeper, boss, antagonist, faction_leader, trainer, guard, civilian
- sources: Source references for this NPC's data (url, domain, tier)

Include BOTH friendly and hostile NPCs:
- Quest givers, vendors, trainers
- Dungeon and raid bosses (e.g., "Hogger", not the generic category "Gnolls")
- Antagonist leaders and villain NPCs
- Faction leaders (allied and enemy)

Extract every named NPC mentioned in the content.

REQUIRED fields for every NPC (validation will reject if missing):
- name: Must not be empty
- occupation: Must not be empty — pick the best fit from the occupation list above
- confidence: A number from 0.0 to 1.0 based on source quality

Optional fields — fill when data is available, leave empty when not:
- personality, motivations, relationships, quest_threads, phased_state, sources

Partial data is better than missing an NPC — include NPCs even if you only have name and occupation.

Sources (prefer higher-tier for conflicts):
{source_info}

--- RAW CONTENT ---

{raw_content}
