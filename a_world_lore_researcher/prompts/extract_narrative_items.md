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
