Cross-reference the following extracted lore data for consistency and completeness.

Zone: {zone_name}
NPCs: {npc_count}
Factions: {faction_count}
Lore entries: {lore_count}
Narrative items: {narrative_item_count}

## Entity Category Validation

Check FIRST — are entities in the correct category?

5. NPCs: Every entry in the NPC list must be a SINGLE NAMED INDIVIDUAL character.
   Flag as a conflict if any NPC entry is actually:
   - A creature type or group (e.g., "Kobolds", "Gnolls", "Murlocs")
   - A faction or organization (e.g., "Defias Brotherhood")
   - A location (e.g., "Northshire Abbey", "Goldshire")
   Miscategorized entities should LOWER the npcs confidence score significantly.

6. Narrative items: Every entry must be a physical IN-GAME OBJECT (weapon, artifact, quest item).
   Flag as a conflict if any narrative item entry is actually:
   - A location (e.g., "Goldshire", "Mirror Lake")
   - An NPC or character (e.g., "Hogger")
   - A faction (e.g., "Defias Brotherhood")
   - An event or concept (e.g., "The First War")
   Miscategorized entities should LOWER the narrative_items confidence score significantly.

## Cross-Category Consistency

1. Are there faction names in the zone's narrative_arc or political_climate that are NOT
   in the factions list? If so, list them as cross-category gaps.
2. Are there NPC names in quest_threads or relationships that are NOT in the npcs list?
3. What percentage of NPCs have empty personality fields? Empty occupation fields? Empty quest_threads?
4. Are any contradictions present between data points?
7. Do factions have empty source lists? If so, flag and lower confidence.

## Scoring

Assign confidence scores per category using the completeness-weighted rubric.
You MUST return a confidence dict with ALL 5 keys. Example:

```json
{{"zone": 0.8, "npcs": 0.7, "factions": 0.5, "lore": 0.8, "narrative_items": 0.4}}
```

Use these exact category keys: `zone`, `npcs`, `factions`, `lore`, `narrative_items`.
Every key must be present. Score range: 0.0 to 1.0.

A category with miscategorized entities (NPCs that are locations, items that are NPCs) should
score no higher than 0.3 regardless of other factors.

Full data:
{full_data}
