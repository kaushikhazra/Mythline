"""Tests for Pydantic models — serialization, deserialization, defaults."""

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.models import (
    BudgetState,
    Conflict,
    CrossReferenceResult,
    FactionData,
    FactionExtractionResult,
    FactionRelation,
    FactionStance,
    ItemSignificance,
    JobStatus,
    JobStatusUpdate,
    LoreCategory,
    LoreData,
    LoreExtractionResult,
    MessageEnvelope,
    MessageType,
    NPCData,
    NPCExtractionResult,
    NPCRelationship,
    NarrativeItemData,
    NarrativeItemExtractionResult,
    PhaseState,
    ResearchCheckpoint,
    ResearchJob,
    ResearchPackage,
    SourceReference,
    SourceTier,
    UserDecisionRequired,
    UserDecisionResponse,
    ValidationFeedback,
    ValidationResult,
    ZoneData,
    ZoneFailure,
)
from tests.factories import (
    make_cross_ref,
    make_faction,
    make_item,
    make_lore,
    make_npc,
    make_source,
    make_zone,
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
    def test_rejects_missing_required_fields(self):
        """ZoneData requires narrative_arc, political_climate, connected_zones, era, confidence."""
        with pytest.raises(ValidationError):
            ZoneData(name="Elwynn Forest")

    def test_optional_fields_default(self):
        zone = make_zone()
        assert zone.game == "wow"
        assert zone.level_range == {"min": 0, "max": 0}
        assert zone.access_gating == []

    def test_full_zone(self):
        zone = make_zone(
            name="Elwynn Forest",
            level_range={"min": 1, "max": 10},
            connected_zones=["westfall", "stormwind_city", "redridge_mountains"],
            phase_states=[PhaseState(phase_name="default", description="Peaceful forest")],
            confidence=0.9,
        )
        data = json.loads(zone.model_dump_json())
        assert data["level_range"]["min"] == 1
        assert len(data["connected_zones"]) == 3
        assert data["phase_states"][0]["phase_name"] == "default"

    def test_rejects_confidence_out_of_range(self):
        with pytest.raises(ValidationError):
            make_zone(confidence=1.5)

    def test_rejects_short_narrative_arc(self):
        with pytest.raises(ValidationError):
            make_zone(narrative_arc="Too short")

    def test_rejects_empty_connected_zones(self):
        with pytest.raises(ValidationError):
            make_zone(connected_zones=[])


class TestNPCData:
    def test_rejects_missing_required_fields(self):
        """NPCData requires name, occupation, confidence."""
        with pytest.raises(ValidationError):
            NPCData()

    def test_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            make_npc(name="")

    def test_rejects_confidence_out_of_range(self):
        with pytest.raises(ValidationError):
            make_npc(confidence=-0.1)

    def test_with_relationships(self):
        npc = make_npc(
            name="Marshal Dughan",
            zone_id="elwynn_forest",
            faction_ids=["stormwind"],
            occupation="quest_giver",
            relationships=[
                NPCRelationship(npc_id="deputy_rainer", relationship_type="subordinate"),
            ],
        )
        assert npc.relationships[0].npc_id == "deputy_rainer"
        data = npc.model_dump()
        restored = NPCData(**data)
        assert restored.relationships[0].relationship_type == "subordinate"


class TestFactionData:
    def test_rejects_missing_required_fields(self):
        """FactionData requires name, inter_faction, ideology, goals, confidence."""
        with pytest.raises(ValidationError):
            FactionData(name="Stormwind")

    def test_rejects_empty_inter_faction(self):
        with pytest.raises(ValidationError):
            make_faction(inter_faction=[])

    def test_rejects_empty_goals(self):
        with pytest.raises(ValidationError):
            make_faction(goals=[])

    def test_with_relations(self):
        faction = make_faction(
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
    def test_rejects_missing_required_fields(self):
        """LoreData requires title, content, confidence."""
        with pytest.raises(ValidationError):
            LoreData(title="The Fall of Stormwind")

    def test_rejects_short_content(self):
        with pytest.raises(ValidationError):
            make_lore(content="...")

    def test_rejects_empty_title(self):
        with pytest.raises(ValidationError):
            make_lore(title="")

    def test_category_enum(self):
        lore = make_lore(title="The Fall of Stormwind", category=LoreCategory.HISTORY)
        assert lore.category == LoreCategory.HISTORY
        data = lore.model_dump()
        assert data["category"] == "history"


class TestNarrativeItemData:
    def test_rejects_missing_required_fields(self):
        """NarrativeItemData requires name, story_arc, confidence."""
        with pytest.raises(ValidationError):
            NarrativeItemData(name="Ashbringer")

    def test_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            make_item(name="")

    def test_significance_enum(self):
        item = make_item(name="Ashbringer", significance=ItemSignificance.LEGENDARY)
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

    def test_new_message_types(self):
        assert MessageType.RESEARCH_JOB == "research_job"
        assert MessageType.JOB_STATUS_UPDATE == "job_status_update"


class TestResearchPackage:
    def test_minimal(self):
        pkg = ResearchPackage(zone_name="elwynn_forest", zone_data=make_zone(name="Elwynn Forest"))
        assert pkg.zone_name == "elwynn_forest"
        assert pkg.npcs == []
        assert pkg.conflicts == []
        assert pkg.quality_warnings == []

    def test_quality_warnings_field(self):
        pkg = ResearchPackage(
            zone_name="westfall",
            zone_data=make_zone(name="Westfall"),
            quality_warnings=["shallow_narrative_arc", "missing_antagonists"],
        )
        assert len(pkg.quality_warnings) == 2
        assert "shallow_narrative_arc" in pkg.quality_warnings

    def test_full_package_roundtrip(self):
        source = make_source(url="https://wowpedia.fandom.com/wiki/Elwynn")
        pkg = ResearchPackage(
            zone_name="elwynn_forest",
            zone_data=make_zone(name="Elwynn Forest", confidence=0.9),
            npcs=[make_npc(name="Marshal Dughan", occupation="quest_giver")],
            factions=[make_faction(name="Stormwind")],
            lore=[make_lore(title="History of Elwynn")],
            narrative_items=[make_item(name="Hogger's Claw")],
            sources=[source],
            confidence={"zone_overview": 0.9, "npc_list": 0.8},
            conflicts=[
                Conflict(
                    data_point="Hogger level",
                    source_a=source,
                    claim_a="Level 11",
                    source_b=make_source(url="https://warcraft.wiki.gg/wiki/Hogger", domain="warcraft.wiki.gg", tier=SourceTier.PRIMARY),
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
        cp = ResearchCheckpoint(job_id="job-1", zone_name="elwynn_forest")
        assert cp.job_id == "job-1"
        assert cp.current_step == 0
        assert cp.step_data == {}

    def test_roundtrip(self):
        cp = ResearchCheckpoint(
            job_id="job-abc",
            zone_name="westfall",
            current_step=5,
            step_data={"step_1": {"urls": ["https://example.com"]}},
        )
        json_str = cp.model_dump_json()
        restored = ResearchCheckpoint.model_validate_json(json_str)
        assert restored.job_id == "job-abc"
        assert restored.current_step == 5
        assert restored.zone_name == "westfall"

    def test_no_autonomous_fields(self):
        """Verify removed fields are no longer present."""
        cp = ResearchCheckpoint(job_id="j1", zone_name="test")
        assert not hasattr(cp, "progression_queue")
        assert not hasattr(cp, "priority_queue")
        assert not hasattr(cp, "completed_zones")
        assert not hasattr(cp, "failed_zones")
        assert not hasattr(cp, "daily_tokens_used")
        assert not hasattr(cp, "last_reset_date")


class TestResearchJob:
    def test_defaults(self):
        job = ResearchJob(job_id="abc-123", zone_name="elwynn_forest")
        assert job.job_id == "abc-123"
        assert job.zone_name == "elwynn_forest"
        assert job.depth == 0
        assert job.game == "wow"
        assert job.requested_by == ""
        assert isinstance(job.requested_at, datetime)

    def test_full_job(self):
        job = ResearchJob(
            job_id="xyz-789",
            zone_name="westfall",
            depth=2,
            game="wow",
            requested_by="user-1",
        )
        assert job.depth == 2
        assert job.requested_by == "user-1"

    def test_json_roundtrip(self):
        job = ResearchJob(job_id="test", zone_name="elwynn_forest", depth=1)
        json_str = job.model_dump_json()
        restored = ResearchJob.model_validate_json(json_str)
        assert restored.job_id == "test"
        assert restored.depth == 1


class TestJobStatus:
    def test_all_values(self):
        assert JobStatus.ACCEPTED == "accepted"
        assert JobStatus.ZONE_STARTED == "zone_started"
        assert JobStatus.STEP_PROGRESS == "step_progress"
        assert JobStatus.ZONE_COMPLETED == "zone_completed"
        assert JobStatus.JOB_COMPLETED == "job_completed"
        assert JobStatus.JOB_PARTIAL_COMPLETED == "job_partial_completed"
        assert JobStatus.JOB_FAILED == "job_failed"


class TestZoneFailure:
    def test_create(self):
        zf = ZoneFailure(zone_name="deadwind_pass", error="No data found")
        assert zf.zone_name == "deadwind_pass"
        assert zf.error == "No data found"

    def test_json_roundtrip(self):
        zf = ZoneFailure(zone_name="test", error="timeout")
        restored = ZoneFailure.model_validate_json(zf.model_dump_json())
        assert restored.zone_name == "test"


class TestJobStatusUpdate:
    def test_defaults(self):
        update = JobStatusUpdate(job_id="j1", status=JobStatus.ACCEPTED)
        assert update.job_id == "j1"
        assert update.zone_name == ""
        assert update.step_name == ""
        assert update.zones_completed == 0
        assert update.zones_total == 0
        assert update.zones_failed == []
        assert update.error == ""
        assert isinstance(update.timestamp, datetime)

    def test_full_update(self):
        update = JobStatusUpdate(
            job_id="j1",
            status=JobStatus.JOB_PARTIAL_COMPLETED,
            zones_completed=3,
            zones_total=5,
            zones_failed=[
                ZoneFailure(zone_name="deadwind_pass", error="timeout"),
                ZoneFailure(zone_name="burning_steppes", error="budget"),
            ],
        )
        assert len(update.zones_failed) == 2
        assert update.zones_failed[0].zone_name == "deadwind_pass"

    def test_json_roundtrip(self):
        update = JobStatusUpdate(
            job_id="j1",
            status=JobStatus.STEP_PROGRESS,
            zone_name="elwynn_forest",
            step_name="npc_research",
            step_number=2,
            total_steps=9,
        )
        restored = JobStatusUpdate.model_validate_json(update.model_dump_json())
        assert restored.step_name == "npc_research"
        assert restored.step_number == 2


class TestBudgetState:
    def test_defaults(self):
        bs = BudgetState()
        assert bs.daily_tokens_used == 0
        assert bs.last_reset_date == ""

    def test_with_values(self):
        bs = BudgetState(daily_tokens_used=25000, last_reset_date="2026-02-22")
        assert bs.daily_tokens_used == 25000

    def test_json_roundtrip(self):
        bs = BudgetState(daily_tokens_used=10000, last_reset_date="2026-02-22")
        restored = BudgetState.model_validate_json(bs.model_dump_json())
        assert restored.daily_tokens_used == 10000
        assert restored.last_reset_date == "2026-02-22"


class TestCrossReferenceResult:
    def test_rejects_missing_required_fields(self):
        """CrossReferenceResult requires is_consistent and confidence."""
        with pytest.raises(ValidationError):
            CrossReferenceResult()

    def test_valid(self):
        result = make_cross_ref()
        assert result.is_consistent is True
        assert "zone" in result.confidence

    def test_roundtrip(self):
        result = make_cross_ref(is_consistent=False, notes="NPC mismatch detected")
        data = result.model_dump_json()
        restored = CrossReferenceResult.model_validate_json(data)
        assert restored.is_consistent is False
        assert restored.notes == "NPC mismatch detected"


class TestNPCExtractionResult:
    def test_rejects_empty_npcs(self):
        """NPCExtractionResult requires at least one NPC."""
        with pytest.raises(ValidationError):
            NPCExtractionResult(npcs=[])

    def test_valid(self):
        result = NPCExtractionResult(npcs=[make_npc()])
        assert len(result.npcs) == 1


class TestFactionExtractionResult:
    def test_rejects_empty_factions(self):
        """FactionExtractionResult requires at least one faction."""
        with pytest.raises(ValidationError):
            FactionExtractionResult(factions=[])

    def test_valid(self):
        result = FactionExtractionResult(factions=[make_faction()])
        assert len(result.factions) == 1


class TestLoreExtractionResult:
    def test_rejects_empty_lore(self):
        """LoreExtractionResult requires at least one lore entry."""
        with pytest.raises(ValidationError):
            LoreExtractionResult(lore=[])

    def test_valid(self):
        result = LoreExtractionResult(lore=[make_lore()])
        assert len(result.lore) == 1


class TestNarrativeItemExtractionResult:
    def test_rejects_empty_items(self):
        """NarrativeItemExtractionResult requires at least one item."""
        with pytest.raises(ValidationError):
            NarrativeItemExtractionResult(narrative_items=[])

    def test_valid(self):
        result = NarrativeItemExtractionResult(narrative_items=[make_item()])
        assert len(result.narrative_items) == 1
