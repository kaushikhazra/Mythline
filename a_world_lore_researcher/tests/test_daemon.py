"""Tests for the daemon — job consumer, wave-loop executor, status publishing."""

from unittest.mock import AsyncMock, MagicMock, patch

import aio_pika
import pytest
from pydantic import ValidationError

from src.agent import OrchestratorResult
from src.daemon import (
    Daemon,
    _apply_confidence_caps,
    _compute_quality_warnings,
)
from src.models import (
    Conflict,
    CrossReferenceResult,
    FactionData,
    FactionRelation,
    FactionStance,
    JobStatus,
    JobStatusUpdate,
    LoreData,
    MessageEnvelope,
    MessageType,
    NPCData,
    NarrativeItemData,
    ResearchJob,
    ResearchPackage,
    SourceReference,
    SourceTier,
    ZoneData,
    ZoneExtraction,
)
from tests.factories import (
    make_cross_ref,
    make_extraction,
    make_faction,
    make_item,
    make_lore,
    make_npc,
    make_source,
    make_zone,
)


def _make_job(job_id="job-1", zone_name="elwynn_forest", depth=0):
    return ResearchJob(job_id=job_id, zone_name=zone_name, depth=depth)


def _make_envelope(job: ResearchJob) -> MessageEnvelope:
    return MessageEnvelope(
        source_agent="test",
        target_agent="world_lore_researcher",
        message_type=MessageType.RESEARCH_JOB,
        payload=job.model_dump(mode="json"),
    )


def _make_message(job: ResearchJob) -> MagicMock:
    """Create a mock aio_pika incoming message containing a job."""
    envelope = _make_envelope(job)
    msg = MagicMock()
    msg.body = envelope.model_dump_json().encode()
    msg.ack = AsyncMock()
    msg.nack = AsyncMock()
    return msg


def _make_orchestrator_result(**kwargs) -> OrchestratorResult:
    """Create an OrchestratorResult with sensible defaults."""
    defaults = {
        "zone_data": make_zone(name="elwynn_forest"),
        "npcs": [],
        "factions": [],
        "lore": [],
        "narrative_items": [],
        "sources": [],
        "cross_ref_result": make_cross_ref(
            confidence={"zone": 0.8, "npcs": 0.7},
        ),
        "discovered_zones": [],
        "orchestrator_tokens": 500,
        "worker_tokens": 1000,
    }
    defaults.update(kwargs)
    return OrchestratorResult(**defaults)


def _make_researcher(**kwargs) -> MagicMock:
    """Create a mock LoreResearcher with default orchestrator behavior."""
    researcher = MagicMock()
    researcher.zone_tokens = kwargs.get("zone_tokens", 1500)
    researcher.reset_zone_state = MagicMock()

    result = kwargs.get("result", _make_orchestrator_result())
    researcher.research_zone = AsyncMock(return_value=result)
    return researcher


# --- _publish_status ---


class TestPublishStatus:
    @pytest.mark.asyncio
    async def test_publishes_envelope_to_status_queue(self):
        daemon = Daemon()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_channel.default_exchange = mock_exchange
        daemon._channel = mock_channel

        update = JobStatusUpdate(job_id="j1", status=JobStatus.ACCEPTED)
        await daemon._publish_status(update)

        mock_exchange.publish.assert_called_once()
        call_kwargs = mock_exchange.publish.call_args
        assert call_kwargs[1]["routing_key"] == "agent.world_lore_researcher.status"

        # Verify envelope contents
        published_body = call_kwargs[0][0].body
        envelope = MessageEnvelope.model_validate_json(published_body)
        assert envelope.message_type == MessageType.JOB_STATUS_UPDATE
        assert envelope.source_agent == "world_lore_researcher"

    @pytest.mark.asyncio
    async def test_skips_without_channel(self):
        daemon = Daemon()
        daemon._channel = None

        update = JobStatusUpdate(job_id="j1", status=JobStatus.ACCEPTED)
        # Should not raise
        await daemon._publish_status(update)


# --- _make_publish_fn ---


class TestMakePublishFn:
    @pytest.mark.asyncio
    async def test_publish_fn_sends_to_validator_queue(self):
        daemon = Daemon()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_channel.default_exchange = mock_exchange
        daemon._channel = mock_channel

        publish_fn = daemon._make_publish_fn()
        envelope = MessageEnvelope(
            source_agent="world_lore_researcher",
            target_agent="world_lore_validator",
            message_type=MessageType.RESEARCH_PACKAGE,
            payload={"zone_name": "elwynn_forest"},
        )

        await publish_fn(envelope)

        mock_exchange.publish.assert_called_once()
        call_kwargs = mock_exchange.publish.call_args
        assert call_kwargs[1]["routing_key"] == "agent.world_lore_validator"

    @pytest.mark.asyncio
    async def test_publish_fn_skips_without_channel(self):
        daemon = Daemon()
        daemon._channel = None

        publish_fn = daemon._make_publish_fn()
        envelope = MessageEnvelope(
            source_agent="world_lore_researcher",
            target_agent="world_lore_validator",
            message_type=MessageType.RESEARCH_PACKAGE,
        )
        # Should not raise
        await publish_fn(envelope)


# --- _on_job_message ---


class TestOnJobMessage:
    @pytest.mark.asyncio
    @patch("src.daemon.Daemon._execute_job", new_callable=AsyncMock)
    async def test_valid_job_acks(self, mock_execute):
        daemon = Daemon()
        daemon._channel = AsyncMock()
        researcher = MagicMock()

        job = _make_job()
        msg = _make_message(job)

        await daemon._on_job_message(msg, researcher)

        mock_execute.assert_called_once()
        msg.ack.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_message_nacks(self):
        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()
        researcher = MagicMock()

        msg = MagicMock()
        msg.body = b"not valid json"
        msg.ack = AsyncMock()
        msg.nack = AsyncMock()

        await daemon._on_job_message(msg, researcher)

        msg.nack.assert_called_once_with(requeue=False)
        msg.ack.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._execute_job", new_callable=AsyncMock, side_effect=RuntimeError("boom"))
    async def test_job_failure_nacks_with_actual_error(self, mock_execute, mock_status):
        daemon = Daemon()
        daemon._channel = AsyncMock()
        researcher = MagicMock()

        job = _make_job()
        msg = _make_message(job)

        await daemon._on_job_message(msg, researcher)

        msg.nack.assert_called_once_with(requeue=False)
        msg.ack.assert_not_called()
        # Should publish JOB_FAILED with the actual error message
        status_calls = mock_status.call_args_list
        failed_call = status_calls[-1]
        assert failed_call[0][0].status == JobStatus.JOB_FAILED
        assert failed_call[0][0].error == "boom"


# --- _execute_job ---


class TestExecuteJob:
    @pytest.mark.asyncio
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_single_zone_depth_0(
        self, mock_status, mock_save_budget, mock_load_budget,
    ):
        """Depth 0: research root zone only, skip_discovery=True."""
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState()

        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()

        job = _make_job(depth=0)
        researcher = _make_researcher()

        await daemon._execute_job(job, researcher)

        # research_zone called with skip_discovery=True (depth 0 = last wave)
        researcher.research_zone.assert_called_once_with(
            "elwynn_forest", skip_discovery=True,
        )

        # Verify status flow: ACCEPTED -> ZONE_STARTED -> ZONE_COMPLETED -> JOB_COMPLETED
        statuses = [call[0][0].status for call in mock_status.call_args_list]
        assert statuses[0] == JobStatus.ACCEPTED
        assert JobStatus.ZONE_STARTED in statuses
        assert JobStatus.ZONE_COMPLETED in statuses
        assert statuses[-1] == JobStatus.JOB_COMPLETED

    @pytest.mark.asyncio
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_multi_zone_depth_1(
        self, mock_status, mock_save_budget, mock_load_budget,
    ):
        """Depth 1: research root + discovered neighbors."""
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState()

        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()

        job = _make_job(depth=1)

        call_count = 0

        async def fake_research_zone(zone_name, skip_discovery=False):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Root zone — discovery enabled
                assert not skip_discovery
                return _make_orchestrator_result(
                    discovered_zones=["westfall", "stormwind_city"],
                )
            else:
                # Neighbor zones — discovery skipped (last wave)
                assert skip_discovery
                return _make_orchestrator_result()

        researcher = _make_researcher()
        researcher.research_zone = AsyncMock(side_effect=fake_research_zone)

        await daemon._execute_job(job, researcher)

        # Should have processed 3 zones: root + 2 discovered
        assert call_count == 3

        # Final status should be JOB_COMPLETED
        statuses = [call[0][0].status for call in mock_status.call_args_list]
        assert statuses[-1] == JobStatus.JOB_COMPLETED

    @pytest.mark.asyncio
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_partial_failure(
        self, mock_status, mock_save_budget, mock_load_budget,
    ):
        """Multi-zone job with one zone failing: JOB_PARTIAL_COMPLETED."""
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState()

        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()

        job = _make_job(depth=1)

        call_count = 0

        async def fake_research_zone(zone_name, skip_discovery=False):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Root succeeds, discovers 2 zones
                return _make_orchestrator_result(
                    discovered_zones=["westfall", "stormwind_city"],
                )
            elif call_count == 2:
                # First neighbor fails
                raise RuntimeError("LLM timeout")
            else:
                # Second neighbor succeeds
                return _make_orchestrator_result()

        researcher = _make_researcher()
        researcher.research_zone = AsyncMock(side_effect=fake_research_zone)

        await daemon._execute_job(job, researcher)

        # Final status should be JOB_PARTIAL_COMPLETED
        statuses = [call[0][0].status for call in mock_status.call_args_list]
        assert statuses[-1] == JobStatus.JOB_PARTIAL_COMPLETED

        # Should include the failed zone
        final_update = mock_status.call_args_list[-1][0][0]
        assert len(final_update.zones_failed) == 1
        assert final_update.zones_failed[0].zone_name == "westfall"

    @pytest.mark.asyncio
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_budget_exhausted_raises_without_publishing(
        self, mock_status, mock_save_budget, mock_load_budget,
    ):
        """Budget exhaustion raises RuntimeError; JOB_FAILED is _on_job_message's job."""
        from datetime import date
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState(
            daily_tokens_used=999_999,
            last_reset_date=date.today().isoformat(),  # Today — won't reset
        )

        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()

        job = _make_job()

        with pytest.raises(RuntimeError, match="budget"):
            await daemon._execute_job(job, MagicMock())

        # Only ACCEPTED should have been published — no JOB_FAILED from _execute_job
        statuses = [call[0][0].status for call in mock_status.call_args_list]
        assert JobStatus.ACCEPTED in statuses
        assert JobStatus.JOB_FAILED not in statuses

    @pytest.mark.asyncio
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_budget_saved_after_zone(
        self, mock_status, mock_save_budget, mock_load_budget,
    ):
        """Budget is persisted after each zone completes (token tracking wired)."""
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState()

        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()

        job = _make_job(depth=0)
        researcher = _make_researcher(zone_tokens=1500)

        await daemon._execute_job(job, researcher)

        # save_budget called: once for initial load+reset, once after zone
        assert mock_save_budget.call_count == 2
        # Second call should have accumulated tokens
        saved_budget = mock_save_budget.call_args_list[1][0][0]
        assert saved_budget.daily_tokens_used == 1500
        researcher.reset_zone_state.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_deduplicates_discovered_zones(
        self, mock_status, mock_save_budget, mock_load_budget,
    ):
        """Zones already completed or pending are not re-queued."""
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState()

        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()

        job = _make_job(zone_name="elwynn_forest", depth=1)

        call_count = 0

        async def fake_research_zone(zone_name, skip_discovery=False):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Root discovers zones including itself
                return _make_orchestrator_result(
                    discovered_zones=["elwynn_forest", "westfall"],
                )
            return _make_orchestrator_result()

        researcher = _make_researcher()
        researcher.research_zone = AsyncMock(side_effect=fake_research_zone)

        await daemon._execute_job(job, researcher)

        # Should process root + westfall only (elwynn_forest deduplicated)
        assert call_count == 2

    @pytest.mark.asyncio
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_all_zones_failed_raises(
        self, mock_status, mock_save_budget, mock_load_budget,
    ):
        """All zones failing raises RuntimeError (triggers JOB_FAILED + nack in caller)."""
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState()

        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()

        job = _make_job(depth=1)

        call_count = 0

        async def fake_research_zone(zone_name, skip_discovery=False):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("root failed")
            raise RuntimeError("zone failed")

        researcher = _make_researcher()
        researcher.research_zone = AsyncMock(side_effect=fake_research_zone)

        with pytest.raises(RuntimeError, match="all zones failed"):
            await daemon._execute_job(job, researcher)

        # No JOB_PARTIAL_COMPLETED or JOB_COMPLETED should have been published
        statuses = [call[0][0].status for call in mock_status.call_args_list]
        assert JobStatus.JOB_PARTIAL_COMPLETED not in statuses
        assert JobStatus.JOB_COMPLETED not in statuses

    @pytest.mark.asyncio
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_all_zones_failed_nacks_via_on_job_message(
        self, mock_status, mock_save_budget, mock_load_budget,
    ):
        """All-zones-failed RuntimeError propagates to _on_job_message which nacks."""
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState()

        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()

        job = _make_job(depth=0)
        msg = _make_message(job)

        researcher = _make_researcher()
        researcher.research_zone = AsyncMock(side_effect=RuntimeError("zone exploded"))

        await daemon._on_job_message(msg, researcher)

        msg.nack.assert_called_once_with(requeue=False)
        msg.ack.assert_not_called()
        # JOB_FAILED should be published by _on_job_message
        statuses = [call[0][0].status for call in mock_status.call_args_list]
        assert JobStatus.JOB_FAILED in statuses

    @pytest.mark.asyncio
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_publishes_package_to_validator(
        self, mock_status, mock_save_budget, mock_load_budget,
    ):
        """Package is assembled and published to the validator queue."""
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState()

        daemon = Daemon()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_channel.default_exchange = mock_exchange
        daemon._channel = mock_channel

        job = _make_job(depth=0)
        researcher = _make_researcher()

        await daemon._execute_job(job, researcher)

        # Verify publish_fn was called (publishes to validator queue)
        assert mock_exchange.publish.call_count >= 1
        # Find the validator queue publish (routing_key = VALIDATOR_QUEUE)
        validator_publishes = [
            call for call in mock_exchange.publish.call_args_list
            if call[1].get("routing_key") == "agent.world_lore_validator"
        ]
        assert len(validator_publishes) == 1

        # Verify envelope content
        body = validator_publishes[0][0][0].body
        envelope = MessageEnvelope.model_validate_json(body)
        assert envelope.message_type == MessageType.RESEARCH_PACKAGE
        assert envelope.target_agent == "world_lore_validator"

    @pytest.mark.asyncio
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_zone_tokens_logged(
        self, mock_status, mock_save_budget, mock_load_budget,
    ):
        """zone_tokens structured log event is emitted after each zone."""
        import logging
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState()

        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()

        job = _make_job(depth=0)
        result = _make_orchestrator_result(
            orchestrator_tokens=500, worker_tokens=1000,
        )
        researcher = _make_researcher(result=result)

        with patch("src.daemon.logger") as mock_logger:
            await daemon._execute_job(job, researcher)

            # Find the zone_tokens log call
            info_calls = mock_logger.info.call_args_list
            token_calls = [
                call for call in info_calls if call[0][0] == "zone_tokens"
            ]
            assert len(token_calls) == 1
            extra = token_calls[0][1]["extra"]
            assert extra["zone_name"] == "elwynn_forest"
            assert extra["total_tokens"] == 1500
            assert extra["orchestrator_tokens"] == 500
            assert extra["worker_tokens"] == 1000


# --- _assemble_package ---


class TestAssemblePackage:
    def test_assembles_from_full_result(self):
        daemon = Daemon()
        result = _make_orchestrator_result(
            zone_data=make_zone(
                name="elwynn_forest",
                narrative_arc="A long narrative arc " * 20,
            ),
            npcs=[make_npc(name="Marshal McBride", personality="stern", occupation="quest giver")],
            factions=[make_faction(name="Stormwind Guard")],
            lore=[make_lore(title="History of Elwynn")],
            narrative_items=[make_item(name="Marshal's Sword")],
            sources=[make_source(url="https://wow.wiki", domain="wow.wiki", tier=SourceTier.PRIMARY)],
            cross_ref_result=make_cross_ref(
                confidence={"zone": 0.9, "npcs": 0.8, "factions": 0.7},
            ),
        )

        package = daemon._assemble_package(result, "elwynn_forest")

        assert isinstance(package, ResearchPackage)
        assert package.zone_name == "elwynn_forest"
        assert package.zone_data.name == "elwynn_forest"
        assert len(package.npcs) == 1
        assert len(package.factions) == 1
        assert len(package.lore) == 1
        assert len(package.narrative_items) == 1
        assert len(package.sources) == 1
        assert package.confidence["zone"] == 0.9

    def test_fallback_zone_data_when_none(self):
        daemon = Daemon()
        result = _make_orchestrator_result(zone_data=None)

        package = daemon._assemble_package(result, "elwynn_forest")

        assert package.zone_data.name == "elwynn_forest"
        assert "shallow_narrative_arc" in package.quality_warnings

    def test_no_cross_ref_uses_empty_defaults(self):
        daemon = Daemon()
        result = _make_orchestrator_result(cross_ref_result=None)

        package = daemon._assemble_package(result, "elwynn_forest")

        assert package.conflicts == []
        # Confidence dict should still have caps applied (empty base)
        assert isinstance(package.confidence, dict)

    def test_applies_quality_warnings(self):
        daemon = Daemon()
        result = _make_orchestrator_result(
            zone_data=make_zone(name="test", narrative_arc="A" * 51),
        )

        package = daemon._assemble_package(result, "test")

        assert "shallow_narrative_arc" in package.quality_warnings

    def test_applies_confidence_caps(self):
        daemon = Daemon()
        result = _make_orchestrator_result(
            npcs=[],  # No NPCs — should cap npcs confidence
            cross_ref_result=make_cross_ref(
                confidence={"npcs": 0.9},
            ),
        )

        package = daemon._assemble_package(result, "test")

        assert package.confidence["npcs"] <= 0.2


# --- _compute_quality_warnings ---


class TestComputeQualityWarnings:
    def test_shallow_narrative_arc(self):
        extraction = make_extraction(
            zone=make_zone(name="test", narrative_arc="A" * 51),
        )
        warnings = _compute_quality_warnings(extraction)
        assert "shallow_narrative_arc" in warnings

    def test_no_warning_for_long_narrative(self):
        extraction = make_extraction(
            zone=make_zone(name="test", narrative_arc="A" * 300),
        )
        warnings = _compute_quality_warnings(extraction)
        assert "shallow_narrative_arc" not in warnings

    def test_no_npc_personality_data(self):
        extraction = make_extraction(
            zone=make_zone(name="test", narrative_arc="A" * 300),
            npcs=[
                make_npc(name="NPC1", personality=""),
                make_npc(name="NPC2", personality=""),
            ],
        )
        warnings = _compute_quality_warnings(extraction)
        assert "no_npc_personality_data" in warnings

    def test_no_warning_if_some_npcs_have_personality(self):
        extraction = make_extraction(
            zone=make_zone(name="test", narrative_arc="A" * 300),
            npcs=[
                make_npc(name="NPC1", personality="brave"),
                make_npc(name="NPC2", personality=""),
            ],
        )
        warnings = _compute_quality_warnings(extraction)
        assert "no_npc_personality_data" not in warnings

    def test_missing_antagonists(self):
        extraction = make_extraction(
            zone=make_zone(name="test", narrative_arc="The dungeon " + "A" * 300),
            npcs=[make_npc(name="Friendly NPC", occupation="vendor")],
            factions=[make_faction(
                name="Traders",
                inter_faction=[FactionRelation(
                    faction_id="merchants_guild", stance=FactionStance.NEUTRAL,
                )],
            )],
        )
        warnings = _compute_quality_warnings(extraction)
        assert "missing_antagonists" in warnings

    def test_no_missing_antagonists_if_hostile_faction(self):
        extraction = make_extraction(
            zone=make_zone(name="test", narrative_arc="The dungeon " + "A" * 300),
            npcs=[make_npc(name="Friendly NPC", occupation="vendor")],
            factions=[make_faction(
                name="Defias Brotherhood",
                inter_faction=[FactionRelation(
                    faction_id="stormwind", stance=FactionStance.HOSTILE,
                )],
            )],
        )
        warnings = _compute_quality_warnings(extraction)
        assert "missing_antagonists" not in warnings

    def test_no_missing_antagonists_if_boss_npc(self):
        extraction = make_extraction(
            zone=make_zone(name="test", narrative_arc="The dungeon " + "A" * 300),
            npcs=[make_npc(name="Edwin VanCleef", occupation="Boss of the Defias")],
        )
        warnings = _compute_quality_warnings(extraction)
        assert "missing_antagonists" not in warnings

    def test_lore_dungeon_reference_triggers_check(self):
        extraction = make_extraction(
            zone=make_zone(name="test", narrative_arc="A" * 300),
            lore=[make_lore(title="History", content="The raid was epic " * 5)],
            npcs=[make_npc(name="NPC", occupation="vendor")],
        )
        warnings = _compute_quality_warnings(extraction)
        assert "missing_antagonists" in warnings


# --- _apply_confidence_caps ---


class TestApplyConfidenceCaps:
    def test_caps_npcs_when_empty(self):
        extraction = make_extraction(npcs=[])
        confidence = {"npcs": 0.9, "zone": 0.8}
        result = _apply_confidence_caps(extraction, confidence)
        assert result["npcs"] <= 0.2
        assert result["zone"] == 0.8

    def test_caps_factions_when_empty(self):
        extraction = make_extraction(factions=[])
        confidence = {"factions": 0.9}
        result = _apply_confidence_caps(extraction, confidence)
        assert result["factions"] <= 0.2

    def test_caps_npcs_when_majority_missing_personality(self):
        extraction = make_extraction(
            npcs=[
                make_npc(name="NPC1", personality=""),
                make_npc(name="NPC2", personality=""),
                make_npc(name="NPC3", personality="brave"),
            ],
        )
        confidence = {"npcs": 0.9}
        result = _apply_confidence_caps(extraction, confidence)
        assert result["npcs"] <= 0.4

    def test_rejects_npc_with_empty_occupation(self):
        """NPCData.occupation now has min_length=1 — empty occupations are rejected at validation."""
        with pytest.raises(ValidationError):
            NPCData(name="NPC1", occupation="", confidence=0.8)

    def test_no_cap_when_npcs_complete(self):
        extraction = make_extraction(
            npcs=[
                make_npc(name="NPC1", personality="brave", occupation="guard"),
                make_npc(name="NPC2", personality="shy", occupation="vendor"),
            ],
        )
        confidence = {"npcs": 0.9}
        result = _apply_confidence_caps(extraction, confidence)
        assert result["npcs"] == 0.9

    def test_does_not_mutate_input(self):
        extraction = make_extraction(npcs=[])
        confidence = {"npcs": 0.9}
        result = _apply_confidence_caps(extraction, confidence)
        assert confidence["npcs"] == 0.9  # Original unchanged
        assert result["npcs"] <= 0.2


# --- ResearchJob validation ---


class TestResearchJobValidation:
    def test_rejects_empty_zone_name(self):
        with pytest.raises(ValidationError):
            _make_job(zone_name="")

    def test_rejects_negative_depth(self):
        with pytest.raises(ValidationError):
            _make_job(depth=-1)

    def test_rejects_depth_over_5(self):
        with pytest.raises(ValidationError):
            _make_job(depth=6)

    def test_accepts_valid_depth_range(self):
        for d in (0, 1, 3, 5):
            job = _make_job(depth=d)
            assert job.depth == d


# --- Signal handling ---


class TestSignalHandling:
    def test_handle_signal_stops_daemon(self):
        daemon = Daemon()
        daemon._running = True
        daemon._handle_signal()
        assert daemon._running is False
