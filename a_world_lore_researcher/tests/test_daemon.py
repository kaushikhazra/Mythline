"""Tests for the daemon — job consumer, wave-loop executor, status publishing."""

from unittest.mock import AsyncMock, MagicMock, patch

import aio_pika
import pytest

from src.daemon import Daemon, TOTAL_STEPS
from src.models import (
    JobStatus,
    JobStatusUpdate,
    MessageEnvelope,
    MessageType,
    ResearchCheckpoint,
    ResearchJob,
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
    @patch("src.daemon.Daemon._cleanup_job_checkpoints", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._execute_job", new_callable=AsyncMock)
    async def test_valid_job_acks(self, mock_execute, mock_cleanup):
        daemon = Daemon()
        daemon._channel = AsyncMock()
        researcher = MagicMock()

        job = _make_job()
        msg = _make_message(job)

        await daemon._on_job_message(msg, researcher)

        mock_execute.assert_called_once()
        msg.ack.assert_called_once()
        mock_cleanup.assert_called_once_with("job-1")

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
    @patch("src.daemon.list_checkpoints", new_callable=AsyncMock, return_value=[])
    @patch("src.daemon.load_checkpoint", new_callable=AsyncMock, return_value=None)
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.run_pipeline", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_single_zone_depth_0(
        self, mock_status, mock_pipeline, mock_save_budget, mock_load_budget,
        mock_load_cp, mock_list_cp,
    ):
        """Depth 0: research root zone only, skip discover_connected_zones."""
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState()

        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()

        job = _make_job(depth=0)

        async def fake_pipeline(cp, researcher, publish_fn, skip_steps=None, on_step_progress=None):
            assert skip_steps == {"discover_connected_zones"}
            cp.current_step = TOTAL_STEPS
            return cp

        mock_pipeline.side_effect = fake_pipeline

        await daemon._execute_job(job, MagicMock())

        # Verify status flow: ACCEPTED -> ZONE_STARTED -> ZONE_COMPLETED -> JOB_COMPLETED
        statuses = [call[0][0].status for call in mock_status.call_args_list]
        assert statuses[0] == JobStatus.ACCEPTED
        assert JobStatus.ZONE_STARTED in statuses
        assert JobStatus.ZONE_COMPLETED in statuses
        assert statuses[-1] == JobStatus.JOB_COMPLETED

    @pytest.mark.asyncio
    @patch("src.daemon.list_checkpoints", new_callable=AsyncMock, return_value=[])
    @patch("src.daemon.load_checkpoint", new_callable=AsyncMock, return_value=None)
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.run_pipeline", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_multi_zone_depth_1(
        self, mock_status, mock_pipeline, mock_save_budget, mock_load_budget,
        mock_load_cp, mock_list_cp,
    ):
        """Depth 1: research root + discovered neighbors."""
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState()

        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()

        job = _make_job(depth=1)

        call_count = 0

        async def fake_pipeline(cp, researcher, publish_fn, skip_steps=None, on_step_progress=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Root zone — discover_connected_zones enabled
                assert skip_steps is None
                cp.step_data["discovered_zones"] = ["westfall", "stormwind_city"]
            else:
                # Neighbor zones — discover_connected_zones skipped
                assert skip_steps == {"discover_connected_zones"}
            cp.current_step = TOTAL_STEPS
            return cp

        mock_pipeline.side_effect = fake_pipeline

        await daemon._execute_job(job, MagicMock())

        # Should have processed 3 zones: root + 2 discovered
        assert call_count == 3

        # Final status should be JOB_COMPLETED
        statuses = [call[0][0].status for call in mock_status.call_args_list]
        assert statuses[-1] == JobStatus.JOB_COMPLETED

    @pytest.mark.asyncio
    @patch("src.daemon.list_checkpoints", new_callable=AsyncMock)
    @patch("src.daemon.load_checkpoint", new_callable=AsyncMock)
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.run_pipeline", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_crash_recovery_skips_completed(
        self, mock_status, mock_pipeline, mock_save_budget, mock_load_budget,
        mock_load_cp, mock_list_cp,
    ):
        """Crash recovery: completed zones are detected and skipped."""
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState()

        # Simulate existing checkpoint for root zone (completed)
        mock_list_cp.return_value = ["world_lore_researcher:job-1:elwynn_forest"]

        completed_cp = ResearchCheckpoint(
            job_id="job-1",
            zone_name="elwynn_forest",
            current_step=TOTAL_STEPS,
        )
        mock_load_cp.return_value = completed_cp

        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()

        job = _make_job(depth=0)

        await daemon._execute_job(job, MagicMock())

        # Pipeline should NOT have been called — zone already completed
        mock_pipeline.assert_not_called()

        # Final status should still be JOB_COMPLETED
        statuses = [call[0][0].status for call in mock_status.call_args_list]
        assert statuses[-1] == JobStatus.JOB_COMPLETED

    @pytest.mark.asyncio
    @patch("src.daemon.list_checkpoints", new_callable=AsyncMock, return_value=[])
    @patch("src.daemon.load_checkpoint", new_callable=AsyncMock, return_value=None)
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.run_pipeline", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_partial_failure(
        self, mock_status, mock_pipeline, mock_save_budget, mock_load_budget,
        mock_load_cp, mock_list_cp,
    ):
        """Multi-zone job with one zone failing: JOB_PARTIAL_COMPLETED."""
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState()

        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()

        job = _make_job(depth=1)

        call_count = 0

        async def fake_pipeline(cp, researcher, publish_fn, skip_steps=None, on_step_progress=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Root succeeds, discovers 2 zones
                cp.step_data["discovered_zones"] = ["westfall", "stormwind_city"]
                cp.current_step = TOTAL_STEPS
                return cp
            elif call_count == 2:
                # First neighbor fails
                raise RuntimeError("LLM timeout")
            else:
                # Second neighbor succeeds
                cp.current_step = TOTAL_STEPS
                return cp

        mock_pipeline.side_effect = fake_pipeline

        await daemon._execute_job(job, MagicMock())

        # Final status should be JOB_PARTIAL_COMPLETED
        statuses = [call[0][0].status for call in mock_status.call_args_list]
        assert statuses[-1] == JobStatus.JOB_PARTIAL_COMPLETED

        # Should include the failed zone
        final_update = mock_status.call_args_list[-1][0][0]
        assert len(final_update.zones_failed) == 1
        assert final_update.zones_failed[0].zone_name == "westfall"

    @pytest.mark.asyncio
    @patch("src.daemon.list_checkpoints", new_callable=AsyncMock, return_value=[])
    @patch("src.daemon.load_checkpoint", new_callable=AsyncMock, return_value=None)
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_budget_exhausted_raises_without_publishing(
        self, mock_status, mock_save_budget, mock_load_budget,
        mock_load_cp, mock_list_cp,
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
    @patch("src.daemon.list_checkpoints", new_callable=AsyncMock)
    @patch("src.daemon.load_checkpoint", new_callable=AsyncMock)
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.run_pipeline", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_crash_recovery_resumes_partial(
        self, mock_status, mock_pipeline, mock_save_budget, mock_load_budget,
        mock_load_cp, mock_list_cp,
    ):
        """Crash recovery: partially completed zones are resumed, not lost."""
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState()

        # Root completed, westfall partially done (step 3 of 9)
        mock_list_cp.return_value = [
            "world_lore_researcher:job-1:elwynn_forest",
            "world_lore_researcher:job-1:westfall",
        ]

        root_cp = ResearchCheckpoint(
            job_id="job-1", zone_name="elwynn_forest",
            current_step=TOTAL_STEPS,
            step_data={"discovered_zones": ["westfall", "stormwind_city"]},
        )
        partial_cp = ResearchCheckpoint(
            job_id="job-1", zone_name="westfall",
            current_step=3,
        )

        def load_side_effect(key):
            if "elwynn_forest" in key:
                return root_cp
            if "westfall" in key:
                return partial_cp
            return None

        mock_load_cp.side_effect = load_side_effect

        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()

        job = _make_job(depth=1)

        call_count = 0

        async def fake_pipeline(cp, researcher, publish_fn, skip_steps=None, on_step_progress=None):
            nonlocal call_count
            call_count += 1
            # All recovered zones should skip discovery (last wave at depth 1)
            assert skip_steps == {"discover_connected_zones"}
            cp.current_step = TOTAL_STEPS
            return cp

        mock_pipeline.side_effect = fake_pipeline

        await daemon._execute_job(job, MagicMock())

        # Should process westfall (resumed) + stormwind_city (discovered from root)
        assert call_count == 2
        statuses = [call[0][0].status for call in mock_status.call_args_list]
        assert statuses[-1] == JobStatus.JOB_COMPLETED

    @pytest.mark.asyncio
    @patch("src.daemon.list_checkpoints", new_callable=AsyncMock)
    @patch("src.daemon.load_checkpoint", new_callable=AsyncMock)
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.run_pipeline", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_crash_recovery_discovers_from_completed(
        self, mock_status, mock_pipeline, mock_save_budget, mock_load_budget,
        mock_load_cp, mock_list_cp,
    ):
        """Crash recovery: discovered zones from completed checkpoints are recovered."""
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState()

        # Root completed with discovered zones, no neighbor checkpoints
        mock_list_cp.return_value = [
            "world_lore_researcher:job-1:elwynn_forest",
        ]

        root_cp = ResearchCheckpoint(
            job_id="job-1", zone_name="elwynn_forest",
            current_step=TOTAL_STEPS,
            step_data={"discovered_zones": ["westfall", "stormwind_city"]},
        )

        def load_side_effect(key):
            if "elwynn_forest" in key:
                return root_cp
            return None

        mock_load_cp.side_effect = load_side_effect

        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()

        job = _make_job(depth=1)

        call_count = 0

        async def fake_pipeline(cp, researcher, publish_fn, skip_steps=None, on_step_progress=None):
            nonlocal call_count
            call_count += 1
            cp.current_step = TOTAL_STEPS
            return cp

        mock_pipeline.side_effect = fake_pipeline

        await daemon._execute_job(job, MagicMock())

        # Should process westfall + stormwind_city (recovered from root's discovered_zones)
        assert call_count == 2
        statuses = [call[0][0].status for call in mock_status.call_args_list]
        assert statuses[-1] == JobStatus.JOB_COMPLETED

    @pytest.mark.asyncio
    @patch("src.daemon.list_checkpoints", new_callable=AsyncMock, return_value=[])
    @patch("src.daemon.load_checkpoint", new_callable=AsyncMock, return_value=None)
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_step_progress_published(
        self, mock_status, mock_save_budget, mock_load_budget,
        mock_load_cp, mock_list_cp,
    ):
        """STEP_PROGRESS status is published for each pipeline step."""
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState()

        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()

        job = _make_job(depth=0)

        # Use real run_pipeline with mocked steps to verify callback wiring
        with pytest.MonkeyPatch.context() as m:
            m.setattr("src.pipeline.save_checkpoint", AsyncMock())

            async def fake_run_pipeline(cp, researcher, publish_fn,
                                        skip_steps=None, on_step_progress=None):
                # Simulate 2 steps firing progress
                if on_step_progress:
                    await on_step_progress("zone_overview_research", 1, 9)
                    await on_step_progress("npc_research", 2, 9)
                cp.current_step = TOTAL_STEPS
                return cp

            m.setattr("src.daemon.run_pipeline", fake_run_pipeline)

            await daemon._execute_job(job, MagicMock())

        statuses = [call[0][0].status for call in mock_status.call_args_list]
        assert statuses.count(JobStatus.STEP_PROGRESS) == 2

        # Verify step details in STEP_PROGRESS updates
        step_updates = [
            call[0][0] for call in mock_status.call_args_list
            if call[0][0].status == JobStatus.STEP_PROGRESS
        ]
        assert step_updates[0].step_name == "zone_overview_research"
        assert step_updates[0].step_number == 1
        assert step_updates[0].total_steps == 9
        assert step_updates[1].step_name == "npc_research"

    @pytest.mark.asyncio
    @patch("src.daemon.list_checkpoints", new_callable=AsyncMock, return_value=[])
    @patch("src.daemon.load_checkpoint", new_callable=AsyncMock, return_value=None)
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.run_pipeline", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_budget_saved_after_zone(
        self, mock_status, mock_pipeline, mock_save_budget, mock_load_budget,
        mock_load_cp, mock_list_cp,
    ):
        """Budget is persisted after each zone completes (token tracking wired)."""
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState()

        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()

        job = _make_job(depth=0)

        # Researcher with zone_tokens tracking
        researcher = MagicMock()
        researcher.zone_tokens = 1500
        researcher.reset_zone_tokens = MagicMock()

        async def fake_pipeline(cp, researcher, publish_fn, skip_steps=None, on_step_progress=None):
            cp.current_step = TOTAL_STEPS
            return cp

        mock_pipeline.side_effect = fake_pipeline

        await daemon._execute_job(job, researcher)

        # save_budget called: once for initial load+reset, once after zone
        assert mock_save_budget.call_count == 2
        # Second call should have accumulated tokens
        saved_budget = mock_save_budget.call_args_list[1][0][0]
        assert saved_budget.daily_tokens_used == 1500
        researcher.reset_zone_tokens.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.daemon.list_checkpoints", new_callable=AsyncMock, return_value=[])
    @patch("src.daemon.load_checkpoint", new_callable=AsyncMock, return_value=None)
    @patch("src.daemon.load_budget", new_callable=AsyncMock)
    @patch("src.daemon.save_budget", new_callable=AsyncMock)
    @patch("src.daemon.run_pipeline", new_callable=AsyncMock)
    @patch("src.daemon.Daemon._publish_status", new_callable=AsyncMock)
    async def test_deduplicates_discovered_zones(
        self, mock_status, mock_pipeline, mock_save_budget, mock_load_budget,
        mock_load_cp, mock_list_cp,
    ):
        """Zones already completed or pending are not re-queued."""
        from src.models import BudgetState
        mock_load_budget.return_value = BudgetState()

        daemon = Daemon()
        daemon._channel = AsyncMock()
        daemon._channel.default_exchange = AsyncMock()

        job = _make_job(zone_name="elwynn_forest", depth=1)

        call_count = 0

        async def fake_pipeline(cp, researcher, publish_fn, skip_steps=None, on_step_progress=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Root discovers zones including itself
                cp.step_data["discovered_zones"] = ["elwynn_forest", "westfall"]
            cp.current_step = TOTAL_STEPS
            return cp

        mock_pipeline.side_effect = fake_pipeline

        await daemon._execute_job(job, MagicMock())

        # Should process root + westfall only (elwynn_forest deduplicated)
        assert call_count == 2


# --- Signal handling ---


class TestSignalHandling:
    def test_handle_signal_stops_daemon(self):
        daemon = Daemon()
        daemon._running = True
        daemon._handle_signal()
        assert daemon._running is False
