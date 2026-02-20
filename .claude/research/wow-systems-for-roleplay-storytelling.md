# WoW Systems Research for Roleplay Storytelling Data Model Validation

## Purpose
Validate the proposed data model against WoW's actual game systems to identify gaps, missing concepts, and structural mismatches that matter for roleplay storytelling.

## Proposed Data Model Under Review
```
World Graph: Zone, NPC, Faction, Quest/Event, Lore
Character: Identity, Nature, Reputation Graph, Journal, Growth Arc
Interaction: Scene context assembled from above
```

---

## 1. Faction System

### How It Works
WoW has a layered faction system:

**Primary Factions (Binary):** Alliance vs Horde. Every player character belongs to one. This is immutable (with rare paid exceptions) and determines which cities you enter, which NPCs speak to you, and which players you can group with.

**Sub-Factions (Reputation-Based):** Hundreds of smaller factions with an 8-tier reputation scale:
- Hated -> Hostile -> Unfriendly -> Neutral -> Friendly -> Honored -> Revered -> Exalted

Reputation is earned through quests, kills, and turn-ins. Higher reputation unlocks vendors, quest chains, mounts, tabards, and titles. Some factions are mutually exclusive (e.g., Aldor vs Scryers in TBC: raising one lowers the other).

**Neutral Factions:** Organizations like Argent Dawn, Cenarion Circle, and Earthen Ring accept members of both Alliance and Horde. These are critical for RP because they represent ideological allegiance beyond the faction binary.

**Expansion-Specific Factions:** Each expansion introduces its own faction ecosystem (e.g., Pandaria's Golden Lotus/Shado-Pan, Shadowlands' four Covenants, War Within's factions in Khaz Algar).

### What Matters for RP Storytelling
- Faction allegiance shapes who a character can even TALK to, where they can go safely
- Reputation with sub-factions represents earned trust, ideological alignment, or earned enmity
- Mutually exclusive factions create meaningful character choices (Aldor vs Scryers, Oracles vs Frenzyheart)
- Neutral factions allow cross-faction RP narratives
- Reputation is GRANULAR (8 tiers with numeric points within each tier), not binary

### Model Gap Analysis
The proposed model has "Faction" in World Graph and "Reputation Graph" in Character. This is structurally correct. However:

**GAP: Faction Exclusivity Rules.** The model needs to represent that some faction relationships are mutually exclusive. Gaining reputation with Faction A actively DEGRADES reputation with Faction B. This isn't just a parallel reputation graph -- it's a constrained graph with anti-edges.

**GAP: Faction Hierarchy.** Factions nest: Alliance -> Stormwind -> SI:7. The model needs parent-child faction relationships, not a flat list.

**GAP: Faction determines World Access.** A Horde character literally cannot enter Stormwind without being attacked. Faction gates zone access, NPC availability, and quest availability. The World Graph needs faction-gating on Zones and NPCs.

---

## 2. Phasing System (World State Mutation)

### How It Works
Phasing is WoW's mechanism for changing the world based on individual quest progress. Technically, the server selectively sends/withholds game object data based on quest flags on each character.

Two forms:
1. **NPC Phasing:** NPCs appear, disappear, or change behavior based on quest completion. (e.g., after turning in the quest, the named NPC you killed no longer appears)
2. **Terrain/World State Phasing:** Buildings can be destroyed or rebuilt, entire landscape can change (e.g., Wrathgate area on fire after quest completion, Shadow Vault converting from Scourge base to Ebon Blade hub)

Key implications:
- Two players standing in the same spot can see completely different worlds
- Phasing is per-character (not per-account), so alts can be in different phases
- Some phasing is permanent (quest completion locks you into new phase)
- Some phasing is expansion-gated (Cataclysm permanently reshaped zones for everyone)

### What Matters for RP Storytelling
- The world is not static -- it has a "before" and "after" for every major quest chain
- A character's personal world state is defined by their quest completion history
- RP encounters need to account for which "version" of a zone the character is experiencing
- Phasing creates powerful narrative moments: your character literally witnesses the world change

### Model Gap Analysis

**CRITICAL GAP: World State is per-character, not global.** The proposed model has a World Graph (Zone, NPC, Faction, Quest/Event, Lore) that appears to be a single static graph. In WoW, the World Graph is a FUNCTION of the Character's quest history. Zone X might have NPC Y alive for Character A but dead for Character B.

The model needs:
- **World State Versioning:** Zones and NPCs need phase states (version tags keyed to quest completion)
- **Character World View:** A derived view of the World Graph filtered through the character's quest completion flags
- Or at minimum: a "phase" or "world_state" property on the Interaction context that specifies which version of the world this scene takes place in

**GAP: Temporal Layering.** WoW zones can exist in multiple time periods simultaneously (Chromie Time). A zone like Darkshore has a Classic version, a Cataclysm version, and a BFA version. The model needs to handle "which era" alongside "which phase."

---

## 3. Quest Chain Structure

### How It Works
Quest chains are ordered sequences of quests linked by prerequisites. Structures include:

**Linear Chains:** A -> B -> C. Most common. Each quest unlocks the next.

**Branching Chains:** After Quest A, you might get B1 OR B2, or both in parallel. Sometimes these reconverge. Example: Mount Hyjal has a branching section (Goldrinn/Aessina/Tortolla in any order) that reconverges.

**Cross-Zone Chains:** Some chains span multiple zones or even continents. The Dungeon Set 2 chain bounces between zones. War Campaign in BFA spans both continents.

**Faction-Divergent Chains:** Alliance and Horde sometimes share a chain that diverges and reconverges based on faction.

**Chain Length:** Can range from 2-3 quests to 30-40 quests for epic chains.

**Modern Structure (Campaigns):** Since BFA, Blizzard uses "Campaign" quest lines that form the main story of an expansion, tracked separately in the quest log. These are gated by level/progress milestones.

### What Matters for RP Storytelling
- Quest chains ARE the narrative structure. Each quest is a story beat.
- Branching represents player agency moments
- Cross-zone chains create journey narratives
- Campaign quests form the "main story" vs side quests form "character episodes"
- Parallel quest execution within a chain (do B, C, D in any order) is narratively different from sequential

### Model Gap Analysis
The current Mythline parser already handles this well with Mermaid graph-based quest chain representation, edges, parallel detection, and execution ordering. This is a strength of the current model.

**MINOR GAP: Chain Type Classification.** The model doesn't distinguish between "main campaign quest chain" vs "side quest chain" vs "zone story chapter." In WoW, these have different narrative weights. A campaign quest advances the expansion's main plot; a side quest is a self-contained episode.

**MINOR GAP: Faction-Conditional Quests.** Some quests are only available to one faction, or have different versions per faction. The quest model doesn't have a faction-availability field.

---

## 4. Class Fantasy

### How It Works
WoW has 13 classes (as of The War Within), each with a distinct "class fantasy" -- a thematic identity that shapes how the character relates to the world:

- **Paladin:** Champion of the Light, sworn protector, blends martial prowess with holy power. Struggles with righteousness vs pragmatism.
- **Warlock:** Wielder of forbidden fel magic, summons demons. Walks the line between power and corruption.
- **Death Knight:** Raised undead warrior, formerly bound to the Lich King. Struggles with humanity, cursed to cause suffering. The "dark paladin" archetype.
- **Druid:** Nature's guardian, shapeshifter. Connected to the Emerald Dream and the Wild Gods.
- **Priest:** Channel divine or shadow magic. Shadow priests embrace the Void -- a completely different RP flavor from Holy priests.
- **Shaman:** Commune with elemental spirits. Deeply tied to ancestral traditions.
- **Mage:** Arcane scholars. Knowledge-seeking, often arrogant.
- **Rogue:** Shadows and subterfuge. Often connected to intelligence networks (SI:7, Ravenholdt).
- **Warrior:** Pure martial skill. No magical source, defined by discipline and rage.
- **Hunter:** Bond with beasts, survival in the wild. Rangers and beastmasters.
- **Monk:** Pandaren-origin martial arts philosophy. Balance and inner peace.
- **Demon Hunter:** Sacrificed everything to fight the Burning Legion. Literally consumed demonic power.
- **Evoker:** Dracthyr-only. Connected to dragonflights.

### What Matters for RP Storytelling
- Class determines HOW a character interacts with the world's magic systems
- Class fantasy creates internal conflict (Warlock: power at what cost? Death Knight: can I still be human?)
- Class-specific questlines give characters unique narrative hooks (Death Knight starting zone, Warlock green fire quest, Legion Order Hall campaigns)
- The same NPC interaction means something different to a Paladin vs a Warlock
- Class determines which organizations the character belongs to (Paladins: Silver Hand, Warlocks: Black Harvest, etc.)

### Model Gap Analysis

**GAP: Character Class/Class Fantasy.** The proposed model has "Identity" and "Nature" under Character but doesn't explicitly call out Class as a first-class concept. Class is arguably the MOST important identity axis for RP storytelling in WoW, more so than race. It determines:
- What magic/power sources the character uses
- What organizations they belong to
- What internal conflicts they face
- How NPCs might react to them (a Warlock walking into a Paladin encampment)
- What class-specific content they experience

**GAP: Magic System / Power Source.** The model doesn't represent the character's relationship to WoW's magic systems (Light, Void, Arcane, Nature, Fel, Necromantic, Elemental). This is a core RP identity axis.

**GAP: Class-Gated Content.** Some quests, zones (Order Halls), and NPC interactions are class-specific. The World Graph needs class-gating alongside faction-gating.

---

## 5. Race Lore

### How It Works
WoW has ~25 playable races, each with deep backstory:
- Thousand-year histories, ancient civilizations, wars, diaspora events
- Unique starting zones with race-specific narratives (1-10 leveling)
- Heritage armor questlines that explore racial identity
- Racial leader characters and political structures
- Cultural traits: Night Elf connection to nature, Dwarf love of archaeology, Forsaken existential crisis

Race determines:
- Starting zone and initial narrative
- Which faction (some races locked to Alliance or Horde)
- Cultural context for RP (a Tauren Paladin has a VERY different lore justification than a Human Paladin -- Sunwalker vs Silver Hand)
- Visual identity and customization options
- Language (races have their own languages)

### What Matters for RP Storytelling
- Race provides the character's cultural background, upbringing, and worldview
- Race + Class combinations have unique lore implications (Night Elf Demon Hunter has a specific Illidari connection)
- Racial tensions drive RP conflict (Forsaken are feared even by their Horde allies)
- Heritage quests provide character development arcs
- Racial homelands can be destroyed (Teldrassil for Night Elves, Undercity for Forsaken) -- this creates refugee narratives

### Model Gap Analysis
The "Identity" under Character presumably includes race, but:

**GAP: Race-Class Combination Lore.** It's not just "Race" + "Class" independently. The COMBINATION has unique lore (Night Elf Druid is different from Tauren Druid -- different druidic traditions). The model should support combination-specific lore hooks.

**GAP: Racial Homeland / Cultural Context.** A character's race connects them to a specific homeland, cultural tradition, and political structure. This is a relationship between Character.Identity and World.Zone that has narrative weight beyond just "where you start."

**GAP: Displaced Peoples.** After world-changing events, some races lose their homeland (Night Elves after Teldrassil). The character's relationship to their homeland can be "current resident," "exile," "refugee," or "reclaimer." This is dynamic, not static.

---

## 6. World Events

### How It Works
WoW has several categories of world events:

**Seasonal/Holiday Events:** Brewfest, Hallow's End, Winter Veil, Lunar Festival, etc. These recur annually and have their own quest chains, vendors, and activities.

**Pre-Patch Events:** One-time events before each expansion launch. War of Thorns (BFA), Elemental Unrest (Cataclysm), Scourge Invasion (WotLK). These permanently change the world.

**World-Changing Events:** Cataclysm literally reshaped the physical world. Deathwing destroyed zones. Teldrassil burned. The Dark Portal opened. These are permanent, one-directional changes to the world state.

**World Quests / Invasions:** Repeatable dynamic content that simulates ongoing conflict in zones.

### What Matters for RP Storytelling
- Pre-patch and world-changing events are the most narratively powerful -- they represent turning points
- A character who was PRESENT at the Burning of Teldrassil has a fundamentally different story than one who heard about it later
- Seasonal events provide slice-of-life RP moments between the epic conflicts
- World-changing events create "before/after" identity for characters (pre-Cataclysm vs post-Cataclysm)

### Model Gap Analysis

**GAP: Event Temporality.** The model has "Quest/Event" in the World Graph but doesn't distinguish between:
- One-time historical events (happened once, world changed permanently)
- Recurring seasonal events (happen cyclically)
- Ongoing dynamic events (world quests, invasions)
Each has very different narrative treatment.

**GAP: Character Witness / Participation.** "Were you there?" is a fundamental RP question. The Character model needs a way to record which world events the character witnessed or participated in. This is different from quest completion -- it's about personal history intersecting with world history.

**GAP: World Timeline / Era.** The model needs a temporal axis. The world isn't just spatial (zones) -- it's temporal (eras). The same zone in Classic, Cataclysm, BFA, and current expansion is narratively four different places.

---

## 7. Zone Storytelling

### How It Works
Each zone in WoW tells its own self-contained story through:
- A main quest chain (zone storyline) with beginning, middle, climax
- Side quests that flesh out the zone's culture, conflicts, and characters
- Environmental storytelling (ruins, battlefields, ambient NPC dialogue)
- Zone-specific factions and reputation
- Zone-specific dungeons/raids that serve as narrative climax
- Political conflicts between local factions

Examples:
- Westfall: Mystery/detective story about the Defias Brotherhood
- Dragonblight: Ancient dragon graveyard with Wrath-era plot convergence
- Val'sharah: Emerald Nightmare corruption of Night Elf sacred lands
- Each zone has its own NPCs, political tensions, and thematic identity

### What Matters for RP Storytelling
- Zones are not just locations -- they're story containers with narrative arcs
- Zone NPCs have their own politics, relationships, and conflicts
- Environmental details tell stories (a burned village, an abandoned mine)
- The zone's main quest chain is its "story chapter"
- Dungeons at the end of zone quest chains serve as narrative climax

### Model Gap Analysis
The proposed model has "Zone" in the World Graph. This is correct but needs depth:

**GAP: Zone Narrative Arc.** A zone isn't just a location with NPCs -- it has a story arc (setup, conflict, climax, resolution). The model should represent the zone's narrative structure, not just its contents.

**GAP: Zone Political Landscape.** Who controls this zone? What factions are in conflict here? What's the power dynamic? This is a relationship layer between Zone, Faction, and NPC that the flat model doesn't capture.

**GAP: Environmental Storytelling.** Ruins, battlefields, graves, shrines -- these are "lore objects" that tell stories without quest markers. The model needs a concept of ambient/environmental lore tied to locations within a zone.

---

## 8. Dungeon/Raid Lore

### How It Works
Group content (dungeons for 5 players, raids for 10-30) serves as narrative climax points:

- Dungeons often cap zone storylines (Deadmines caps Westfall, Wailing Caverns caps Barrens)
- Raids serve as expansion-ending narrative payoffs (Icecrown Citadel ends WotLK, Antorus ends Legion)
- Boss encounters have backstories, motivations, and dialogue
- Some raids feature in-raid storytelling (cutscenes, NPC assistance, progressive reveals)
- Canonical clears are attributed to specific factions/groups in WoW lore

Modern additions:
- **Delves** (War Within): Solo/small-group mini-dungeons with narrative content, accompanied by NPC companion (Brann Bronzebeard)
- Main story can now flow through dungeons/delves rather than being exclusively raid-gated

### What Matters for RP Storytelling
- Group content represents the character's most epic moments -- confronting major villains, entering legendary locations
- The RP challenge: these are group experiences, but storytelling is often solo-character focused
- Boss encounters are narrative beats (confrontation, revelation, triumph)
- Delves democratize narrative content for solo RP storytelling
- The question "who was in the group?" matters for RP

### Model Gap Analysis

**GAP: Group Content Representation.** The model treats quests as individual experiences. But dungeons and raids are inherently GROUP experiences with MULTIPLE characters. The Interaction model needs a concept of "party" or "group" -- who was there, what roles they played.

**GAP: Boss Encounters as Narrative Beats.** Dungeon/raid bosses are significant NPCs with their own stories, motivations, and dialogue. They're not just "quest objectives" -- they're narrative confrontations. The model needs a concept of "encounter" that's richer than a quest step.

**GAP: Companion NPCs.** Modern content (Delves with Brann) features NPC companions who fight alongside you, have dialogue, and develop their own arcs. This is a new relationship type: NPC-as-party-member rather than NPC-as-quest-giver.

---

## 9. Expansion-Specific Narrative Systems (Borrowed Power)

### How It Works
Each expansion introduces narrative systems that are active for that expansion only:

- **Garrisons (WoD):** Personal fortress you build up. Follower missions. Commander fantasy.
- **Order Halls (Legion):** Class-specific headquarters shared with all characters of that class. Champions are lore-significant NPCs. Artifact weapons with their own upgrade paths and stories.
- **Heart of Azeroth (BFA):** Amulet that absorbs the world's lifeblood. Represents personal connection to Azeroth-as-entity.
- **Covenants (Shadowlands):** Afterlife factions (Kyrian, Venthyr, Night Fae, Necrolord). Each with unique abilities, armor, story campaign, and soulbinds (binding your soul to an NPC).
- **Warbands (War Within):** Account-wide identity system.

Key pattern: These systems get ABANDONED when the expansion ends. Order Halls became ghost towns after Legion. Covenants became irrelevant after Shadowlands.

### What Matters for RP Storytelling
- These systems represent the CHARACTER'S relationship to the expansion's central conflict
- Order Halls gave characters a class-specific HOME and LEADERSHIP ROLE
- Covenants required a meaningful RP CHOICE (which afterlife faction do you align with?)
- Artifact weapons were narrative companions -- they leveled with you, had their own stories
- The abandonment of these systems is itself a narrative event (why did the Paladin stop being the leader of the Silver Hand?)

### Model Gap Analysis

**CRITICAL GAP: Expansion-Scoped Identity.** The Character model needs a concept of "era-specific identity" -- who the character WAS during each expansion. A Paladin in Legion was the Highlord of the Silver Hand wielding Ashbringer. In BFA, they were just... a Paladin again. The character's role, title, organizational position, and special items change per expansion.

**GAP: Narrative Systems as Character Relationships.** Covenant choice, Order Hall leadership, Garrison command -- these are CHARACTER-ORGANIZATION relationships with narrative weight that the model's flat "Identity" doesn't capture.

**GAP: Borrowed Power Items.** Artifacts, Heart of Azeroth, Covenant abilities -- these are items/powers with their own narrative arcs that the character carries for a time, then loses. The model needs a concept of "temporary narrative artifacts."

---

## 10. Items/Artifacts with Lore

### How It Works
WoW has several tiers of narratively significant items:

**Legendary Items:** Thunderfury, Sulfuras, Warglaives, Shadowmourne, etc. These have elaborate acquisition questlines involving rare drops, faction reputation, and multi-step crafting. Wielding one was a server-notable achievement.

**Artifact Weapons (Legion):** Every class received a legendary artifact (Ashbringer, Doomhammer, Blades of the Fallen Prince). These leveled with the player, had trait trees, and triggered special events. They were narrative companions.

**Heirlooms with Stories:** Ashbringer passed from Mograine to Tirion to the player. Frostmourne passed from the Lich King to shards to the player (as Blades of the Fallen Prince). These items have multi-expansion arcs.

**Transmog and Visual Identity:** The appearance system lets characters wear any previously acquired armor appearance. This means a character's VISUAL identity is a curated choice -- RP characters choose looks that tell their story.

**Titles:** Displayed before/after the character's name. Earned through achievements, quests, reputation, PvP. Examples: "the Kingslayer," "Champion of the Naaru," "the Insane." These are identity statements.

### What Matters for RP Storytelling
- Legendary items define characters. Wielding Ashbringer isn't just a stat boost -- it's a NARRATIVE STATEMENT about who this character is
- The acquisition journey (quest chain, rare drops, group effort) is itself a story arc
- Transmog choices express character identity visually
- Titles are public-facing identity markers that tell other characters something about your history
- Item provenance (who wielded it before you, what history it carries) matters enormously for RP

### Model Gap Analysis

**GAP: Narratively Significant Items.** The model has no "Item" or "Artifact" concept. For RP storytelling, certain items are characters in their own right -- Frostmourne has a story arc, Ashbringer has lineage, Thunderfury has a crafting legend. These need first-class representation.

**GAP: Titles as Identity Layer.** Titles are a key RP expression mechanism. "Highlord [Name]" tells a completely different story than "[Name] the Patient." The Character model needs a titles/honors concept.

**GAP: Visual Identity / Transmog.** How the character LOOKS is a narrative choice in WoW. The model should support character appearance description as part of Identity.

---

## Summary: Gaps in the Proposed Model

### The Proposed Model
```
World Graph: Zone, NPC, Faction, Quest/Event, Lore
Character: Identity, Nature, Reputation Graph, Journal, Growth Arc
Interaction: Scene context assembled from above
```

### CRITICAL Gaps (Would cause incorrect/incomplete storytelling)

| # | Gap | WoW System | Why It Matters |
|---|-----|-----------|----------------|
| 1 | **World State Mutation / Phasing** | Phasing system | The world is not static. The same zone exists in multiple states based on quest progress. The World Graph must be versioned or filtered per-character. |
| 2 | **Temporal / Era Axis** | Chromie Time, expansion progression | WoW's world exists across multiple eras. Zone X in Classic is not Zone X in Cataclysm. Without a time axis, the model conflates different versions of the world. |
| 3 | **Class as First-Class Identity** | Class fantasy, class-specific content | Class is the single most important RP identity axis in WoW. It determines power source, organizations, internal conflict, and class-gated content. It must be more than a property of "Identity." |
| 4 | **Expansion-Scoped Character Identity** | Order Halls, Covenants, Garrisons | A character's role, title, organizational membership, and special items change per expansion. The character isn't static -- they have era-specific identity layers. |
| 5 | **Group Content / Party** | Dungeons, Raids, Delves | Many of WoW's most narratively significant moments are group experiences. The model needs a "party/group" concept for the Interaction layer. |

### SIGNIFICANT Gaps (Would limit storytelling richness)

| # | Gap | WoW System | Why It Matters |
|---|-----|-----------|----------------|
| 6 | **Faction Hierarchy and Exclusivity** | Reputation system | Factions nest (Alliance > Stormwind > SI:7) and some are mutually exclusive. The model needs parent-child and anti-edge relationships. |
| 7 | **Faction/Class Gating on World Access** | Faction cities, class halls | NPCs, zones, and quests are gated by faction AND class. The World Graph needs gating metadata. |
| 8 | **Narratively Significant Items** | Legendaries, Artifacts | Items like Ashbringer are narrative entities with their own story arcs, lineage, and identity weight. No "Item" concept exists in the model. |
| 9 | **Character Event Participation** | World events, pre-patches | "Were you there when Teldrassil burned?" is a core RP question. The Character needs a witness/participation record for world events. |
| 10 | **Zone Narrative Arc** | Zone storytelling | Zones aren't just containers -- they have story arcs with setup/conflict/climax. The model treats zones as static locations. |
| 11 | **Magic System / Power Source** | Class fantasy, WoW cosmology | Light, Void, Arcane, Nature, Fel, Necromantic, Elemental -- these are the "forces" that define how characters interact with the world. Not represented. |

### MINOR Gaps (Nice to have for deep RP)

| # | Gap | WoW System | Why It Matters |
|---|-----|-----------|----------------|
| 12 | **Titles/Honors** | Achievement titles | Public identity markers that signal character history. |
| 13 | **Visual Identity / Transmog** | Transmog system | How a character looks is a curated narrative choice. |
| 14 | **Race-Class Combination Lore** | Racial class variants | Night Elf Druid and Tauren Druid follow different druidic traditions. The combination matters, not just each independently. |
| 15 | **NPC Companions** | Delves companion, Order Hall champions | NPCs as party members, not just quest givers. A different relationship type. |
| 16 | **Quest Chain Type Classification** | Campaigns vs side quests | Main story vs zone story vs side quest have different narrative weights. |
| 17 | **Environmental Lore Objects** | Ruins, shrines, battlefields | Ambient storytelling without quest markers. |
| 18 | **Displaced Peoples / Refugee Status** | Teldrassil, Undercity destruction | Character's relationship to homeland can be dynamic (resident, exile, refugee). |
| 19 | **Event Temporality Types** | Seasonal vs one-time vs ongoing | Different event types have different narrative treatment. |

---

## Recommended Model Evolution

Based on this research, the model would benefit from these structural additions:

### World Graph Additions
```
World Graph:
  Zone:
    + era/expansion (temporal axis)
    + phase_states[] (versioned based on quest completion)
    + narrative_arc (setup/conflict/climax/resolution)
    + political_landscape (controlling faction, contested status)
    + ambient_lore[] (environmental storytelling objects)
  NPC:
    + faction_gating (which factions can interact)
    + class_gating (which classes can interact)
    + companion_role (quest_giver | vendor | companion | boss | ambient)
  Faction:
    + parent_faction (hierarchy)
    + exclusive_with[] (mutually exclusive factions)
    + era_scope (which expansion/era this faction is active in)
  Quest/Event:
    + type (campaign | zone_story | side_quest | world_event | seasonal)
    + temporality (one_time | recurring | ongoing)
    + faction_availability
    + class_availability
    + phase_trigger (what world state change this quest causes)
  Lore:
    (no major gaps here)
  Item (NEW):
    + narrative_significance (legendary | artifact | heirloom | mundane)
    + lineage (previous wielders, origin story)
    + era_scope (when the character holds this item)
```

### Character Additions
```
Character:
  Identity:
    + class (as first-class concept, not just a property)
    + power_source (Light, Void, Arcane, Nature, Fel, etc.)
    + race_class_tradition (e.g., "Sunwalker" for Tauren Paladin)
    + titles[] (earned honors/titles)
    + visual_identity (appearance description)
  Nature:
    (maps to class fantasy internal conflicts)
  Reputation Graph:
    + mutual_exclusion_rules
  Journal:
    + event_participation[] (world events witnessed/participated in)
    + era_identity[] (role/title/org per expansion era)
  Growth Arc:
    + significant_items[] (items with narrative weight)
    + homeland_status (resident | exile | refugee | reclaimer)
```

### Interaction Additions
```
Interaction:
  Scene Context:
    + world_phase (which version of the world this scene occurs in)
    + era (which expansion/time period)
    + party[] (other characters present -- for group content)
    + companion_npcs[] (NPC allies in the scene)
```

---

## Sources

- [Reputation - Wowpedia](https://wowpedia.fandom.com/wiki/Reputation)
- [Phasing - Wowpedia](https://wowpedia.fandom.com/wiki/Phasing)
- [Quest Chain - Wowpedia](https://wowpedia.fandom.com/wiki/Quest_chain)
- [Class Hall - Wowpedia](https://wowpedia.fandom.com/wiki/Class_Hall)
- [Event - Wowpedia](https://wowpedia.fandom.com/wiki/Event)
- [Playable Race - Warcraft Wiki](https://warcraft.wiki.gg/wiki/Playable_race)
- [Title - Warcraft Wiki](https://warcraft.wiki.gg/wiki/Title)
- [Chromie Time - Wowhead](https://www.wowhead.com/guide/chromie-time-leveling-zone-expansion-scaling)
- [Storytelling Through Raids](https://thepatchnotes.com/storytelling-through-raids-how-lore-enriches-the-wow-experience/)
- [Expansion-Locked Systems - BlizzardWatch](https://blizzardwatch.com/2020/07/21/garrisons-artifacts-heart-azeroth-covenants-world-warcraft-focus-much-expansion-locked-systems/)
- [Zone Storytelling - Engadget](https://www.engadget.com/2014-04-16-the-world-as-a-story-emergent-storytelling-in-world-of-warcraft.html)
- [WoW Legendary Weapons](https://armada-online.com/legendary-weapons-in-world-of-warcraft-stories-behind-iconic-weapons/)
- [Delves in War Within - PC Gamer](https://www.pcgamer.com/games/world-of-warcraft/wow-the-war-within-will-tell-its-main-story-via-delves-and-dungeons-when-it-makes-sense-giving-me-hope-for-an-escape-from-2-decades-of-raid-centric-storytelling/)
