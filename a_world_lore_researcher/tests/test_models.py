"""Tests for Pydantic models — serialization, deserialization, defaults."""

import json
from datetime import datetime

from src.models import (
    BudgetState,
    Conflict,
    FactionData,
    FactionRelation,
    FactionStance,
    ItemSignificance,
    JobStatus,
    JobStatusUpdate,
    LoreCategory,
    LoreData,
    MessageEnvelope,
    MessageType,
    NPCData,
    NPCRelationship,
    NarrativeItemData,
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

    def test_new_message_types(self):
        assert MessageType.RESEARCH_JOB == "research_job"
        assert MessageType.JOB_STATUS_UPDATE == "job_status_update"


class TestResearchPackage:
    def test_minimal(self):
        pkg = ResearchPackage(zone_name="elwynn_forest", zone_data=ZoneData(name="Elwynn Forest"))
        assert pkg.zone_name == "elwynn_forest"
        assert pkg.npcs == []
        assert pkg.conflicts == []
        assert pkg.quality_warnings == []

    def test_quality_warnings_field(self):
        pkg = ResearchPackage(
            zone_name="westfall",
            zone_data=ZoneData(name="Westfall"),
            quality_warnings=["shallow_narrative_arc", "missing_antagonists"],
        )
        assert len(pkg.quality_warnings) == 2
        assert "shallow_narrative_arc" in pkg.quality_warnings

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
