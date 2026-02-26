"""Test factories for creating valid model instances.

Every domain model with required Field() constraints needs a factory that
provides sensible defaults so tests can construct instances without
repeating boilerplate. Tests override only the fields they care about.
"""

from src.models import (
    Conflict,
    CrossReferenceResult,
    FactionData,
    FactionExtractionResult,
    FactionRelation,
    FactionStance,
    LoreData,
    LoreExtractionResult,
    NarrativeItemData,
    NarrativeItemExtractionResult,
    NPCData,
    NPCExtractionResult,
    SourceReference,
    SourceTier,
    ZoneData,
    ZoneExtraction,
)


def make_zone(**overrides) -> ZoneData:
    defaults = dict(
        name="Test Zone",
        narrative_arc="A detailed narrative arc for testing purposes that exceeds the minimum length.",
        political_climate="Contested between factions",
        connected_zones=["adjacent_zone"],
        era="Classic",
        confidence=0.8,
    )
    defaults.update(overrides)
    return ZoneData(**defaults)


def make_npc(**overrides) -> NPCData:
    defaults = dict(
        name="Test NPC",
        occupation="quest_giver",
        confidence=0.8,
    )
    defaults.update(overrides)
    return NPCData(**defaults)


def make_faction(**overrides) -> FactionData:
    defaults = dict(
        name="Test Faction",
        ideology="Protect the realm",
        goals=["Defend territory"],
        inter_faction=[FactionRelation(
            faction_id="other_faction",
            stance=FactionStance.HOSTILE,
        )],
        confidence=0.8,
    )
    defaults.update(overrides)
    return FactionData(**defaults)


def make_lore(**overrides) -> LoreData:
    defaults = dict(
        title="Test Lore Entry",
        content="A detailed lore entry with enough content to pass the minimum length validation.",
        confidence=0.8,
    )
    defaults.update(overrides)
    return LoreData(**defaults)


def make_item(**overrides) -> NarrativeItemData:
    defaults = dict(
        name="Test Item",
        story_arc="Found during a pivotal quest",
        confidence=0.8,
    )
    defaults.update(overrides)
    return NarrativeItemData(**defaults)


def make_cross_ref(**overrides) -> CrossReferenceResult:
    defaults = dict(
        is_consistent=True,
        confidence={
            "zone": 0.9,
            "npcs": 0.8,
            "factions": 0.7,
            "lore": 0.8,
            "narrative_items": 0.7,
        },
    )
    defaults.update(overrides)
    return CrossReferenceResult(**defaults)


def make_extraction(**overrides) -> ZoneExtraction:
    defaults = dict(
        zone=make_zone(),
    )
    defaults.update(overrides)
    return ZoneExtraction(**defaults)


def make_source(**overrides) -> SourceReference:
    defaults = dict(
        url="https://wowpedia.fandom.com/wiki/Test",
        domain="wowpedia.fandom.com",
        tier=SourceTier.OFFICIAL,
    )
    defaults.update(overrides)
    return SourceReference(**defaults)
