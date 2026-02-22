"""Tests for Pydantic models — serialization, deserialization, defaults."""

import json
from datetime import datetime

from src.models import (
    Conflict,
    FailedZone,
    FactionData,
    FactionRelation,
    FactionStance,
    ItemSignificance,
    LoreCategory,
    LoreData,
    MessageEnvelope,
    MessageType,
    NPCData,
    NPCRelationship,
    NarrativeItemData,
    PhaseState,
    ResearchCheckpoint,
    ResearchPackage,
    SourceReference,
    SourceTier,
    UserDecisionRequired,
    UserDecisionResponse,
    ValidationFeedback,
    ValidationResult,
    ZoneData,
)


class TestSourceReference:
    def test_create_with_defaults(self):
        ref = SourceReference(url="https://wowpedia.fandom.com/wiki/Elwynn", domain="wowpedia.fandom.com", tier=SourceTier.OFFICIAL)
        assert ref.url == "https://wowpedia.fandom.com/wiki/Elwynn"
        assert ref.tier == SourceTier.OFFICIAL
        assert isinstance(ref.accessed_at, datetime)

    def test_serialization_roundtrip(self):
        ref = SourceReference(url="https://example.com", domain="example.com", tier=SourceTier.PRIMARY)
        data = ref.model_dump()
        restored = SourceReference(**data)
        assert restored.url == ref.url
        assert restored.tier == ref.tier

    def test_json_roundtrip(self):
        ref = SourceReference(url="https://example.com", domain="example.com", tier=SourceTier.SECONDARY)
        json_str = ref.model_dump_json()
        restored = SourceReference.model_validate_json(json_str)
        assert restored.url == ref.url


class TestZoneData:
    def test_defaults(self):
        zone = ZoneData(name="Elwynn Forest")
        assert zone.name == "Elwynn Forest"
        assert zone.game == "wow"
        assert zone.level_range == {"min": 0, "max": 0}
        assert zone.access_gating == []
        assert zone.confidence == 0.0

    def test_full_zone(self):
        zone = ZoneData(
            name="Elwynn Forest",
            level_range={"min": 1, "max": 10},
            narrative_arc="New adventurers begin their journey in this peaceful forest",
            political_climate="Alliance stronghold under Stormwind's protection",
            connected_zones=["westfall", "stormwind_city", "redridge_mountains"],
            phase_states=[PhaseState(phase_name="default", description="Peaceful forest")],
            confidence=0.9,
        )
        data = json.loads(zone.model_dump_json())
        assert data["level_range"]["min"] == 1
        assert len(data["connected_zones"]) == 3
        assert data["phase_states"][0]["phase_name"] == "default"


class TestNPCData:
    def test_with_relationships(self):
        npc = NPCData(
            name="Marshal Dughan",
            zone_id="elwynn_forest",
            faction_ids=["stormwind"],
            role="quest_giver",
            relationships=[
                NPCRelationship(npc_id="deputy_rainer", relationship_type="subordinate"),
            ],
        )
        assert npc.relationships[0].npc_id == "deputy_rainer"
        data = npc.model_dump()
        restored = NPCData(**data)
        assert restored.relationships[0].relationship_type == "subordinate"


class TestFactionData:
    def test_with_relations(self):
        faction = FactionData(
            name="Stormwind",
            level="major_faction",
            inter_faction=[
                FactionRelation(faction_id="horde", stance=FactionStance.HOSTILE),
                FactionRelation(faction_id="ironforge", stance=FactionStance.ALLIED),
            ],
            ideology="Human kingdom of the Eastern Kingdoms",
        )
        assert len(faction.inter_faction) == 2
        assert faction.inter_faction[0].stance == FactionStance.HOSTILE


class TestLoreData:
    def test_category_enum(self):
        lore = LoreData(title="The Fall of Stormwind", category=LoreCategory.HISTORY, content="...")
        assert lore.category == LoreCategory.HISTORY
        data = lore.model_dump()
        assert data["category"] == "history"


class TestNarrativeItemData:
    def test_significance_enum(self):
        item = NarrativeItemData(name="Ashbringer", significance=ItemSignificance.LEGENDARY)
        assert item.significance == ItemSignificance.LEGENDARY


class TestMessageEnvelope:
    def test_auto_generated_fields(self):
        msg = MessageEnvelope(
            source_agent="world_lore_researcher",
            target_agent="world_lore_validator",
            message_type=MessageType.RESEARCH_PACKAGE,
        )
        assert msg.message_id
        assert msg.correlation_id
        assert isinstance(msg.timestamp, datetime)

    def test_json_serialization(self):
        msg = MessageEnvelope(
            source_agent="world_lore_researcher",
            target_agent="world_lore_validator",
            message_type=MessageType.RESEARCH_PACKAGE,
            payload={"zone_name": "elwynn_forest"},
        )
        json_str = msg.model_dump_json()
        restored = MessageEnvelope.model_validate_json(json_str)
        assert restored.payload["zone_name"] == "elwynn_forest"
        assert restored.message_type == MessageType.RESEARCH_PACKAGE


class TestResearchPackage:
    def test_minimal(self):
        pkg = ResearchPackage(zone_name="elwynn_forest", zone_data=ZoneData(name="Elwynn Forest"))
        assert pkg.zone_name == "elwynn_forest"
        assert pkg.npcs == []
        assert pkg.conflicts == []

    def test_full_package_roundtrip(self):
        source = SourceReference(url="https://wowpedia.fandom.com/wiki/Elwynn", domain="wowpedia.fandom.com", tier=SourceTier.OFFICIAL)
        pkg = ResearchPackage(
            zone_name="elwynn_forest",
            zone_data=ZoneData(name="Elwynn Forest", confidence=0.9),
            npcs=[NPCData(name="Marshal Dughan", role="quest_giver")],
            factions=[FactionData(name="Stormwind")],
            lore=[LoreData(title="History of Elwynn")],
            narrative_items=[NarrativeItemData(name="Hogger's Claw")],
            sources=[source],
            confidence={"zone_overview": 0.9, "npc_list": 0.8},
            conflicts=[
                Conflict(
                    data_point="Hogger level",
                    source_a=source,
                    claim_a="Level 11",
                    source_b=SourceReference(url="https://warcraft.wiki.gg/wiki/Hogger", domain="warcraft.wiki.gg", tier=SourceTier.PRIMARY),
                    claim_b="Level 10",
                ),
            ],
        )
        json_str = pkg.model_dump_json()
        restored = ResearchPackage.model_validate_json(json_str)
        assert restored.zone_name == "elwynn_forest"
        assert len(restored.npcs) == 1
        assert len(restored.conflicts) == 1
        assert restored.confidence["zone_overview"] == 0.9


class TestValidationResult:
    def test_accepted(self):
        result = ValidationResult(zone_name="elwynn_forest", accepted=True, iteration=1)
        assert result.accepted is True

    def test_rejected_with_feedback(self):
        result = ValidationResult(
            zone_name="elwynn_forest",
            accepted=False,
            feedback=[
                ValidationFeedback(field="npcs", issue="Missing Hogger", suggestion="Search for Hogger NPC"),
            ],
            iteration=2,
        )
        assert result.accepted is False
        assert len(result.feedback) == 1


class TestUserDecision:
    def test_required(self):
        decision = UserDecisionRequired(
            question="Which zone should we research next?",
            options=["Westfall", "Loch Modan", "Darkshore"],
            context="Elwynn Forest connects to these zones",
        )
        assert len(decision.options) == 3
        assert decision.decision_id

    def test_response(self):
        response = UserDecisionResponse(decision_id="test-123", choice="Westfall")
        assert response.choice == "Westfall"


class TestResearchCheckpoint:
    def test_defaults(self):
        cp = ResearchCheckpoint(zone_name="elwynn_forest")
        assert cp.current_step == 0
        assert cp.step_data == {}
        assert cp.progression_queue == []
        assert cp.daily_tokens_used == 0

    def test_full_checkpoint_roundtrip(self):
        cp = ResearchCheckpoint(
            zone_name="westfall",
            current_step=5,
            step_data={"step_1": {"urls": ["https://example.com"]}, "step_2": {"zone_name": "Westfall"}},
            progression_queue=["redridge_mountains", "duskwood"],
            priority_queue=["stormwind_city"],
            completed_zones=["elwynn_forest"],
            failed_zones=[FailedZone(zone_name="deadwind_pass", reason="No data found", iterations=3)],
            daily_tokens_used=25000,
            last_reset_date="2026-02-21",
        )
        json_str = cp.model_dump_json()
        restored = ResearchCheckpoint.model_validate_json(json_str)
        assert restored.current_step == 5
        assert len(restored.failed_zones) == 1
        assert restored.failed_zones[0].zone_name == "deadwind_pass"
        assert restored.daily_tokens_used == 25000
