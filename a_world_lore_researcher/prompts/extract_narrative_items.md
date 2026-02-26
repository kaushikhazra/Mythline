Extract narrative items and artifacts for the zone '{zone_name}' from the content below.

CRITICAL — What counts as a narrative item:
A narrative item is an IN-GAME OBJECT that a player can obtain, interact with, or that exists as a
physical thing in the game world. It must be a THING, not a person, place, or organization.

Examples of valid narrative items:
- Named weapons or armor with backstory: "Thunderfury", "Ashbringer"
- Quest objects that advance the story: "Bernice's Necklace", "Marshal's Documents", "Hogger's Claw"
- Lore books or scrolls that reveal story content
- Keys, gems, artifacts central to a quest chain or lore event
- Dungeon loot with narrative backstory connecting to the zone's story

Do NOT include: NPCs/creatures (characters are not objects), quest names (a quest is an activity,
not a thing), locations, or factions. These belong in other extraction categories.
Also exclude generic rare drops with no story connection (e.g., "Ratty Old Belt").

A simple test: can a player hold it in their hand or put it in their inventory? If yes, it may
be a narrative item. If no, it belongs elsewhere.

Extract ALL quest items, quest rewards, and story artifacts you find in the content — even minor
ones. More items with real story connections is better than too few.

For EACH item with genuine narrative significance, extract:
- name: The item's name (must be a physical object)
- story_arc: How this item fits into the zone's story
- wielder_lineage: List of known wielders or owners in order
- power_description: What the item does or represents
- significance: One of: legendary, epic, quest, notable
- sources: Source references for this item's data (url, domain, tier)

Do NOT include: crafting recipes, cooking items, vendor trash, generic consumables, profession materials.
If the zone has no truly significant narrative items, return an empty list — an empty list is far
better than listing locations, NPCs, or factions as items.

Sources (prefer higher-tier for conflicts):
{source_info}

--- RAW CONTENT ---

{raw_content}
