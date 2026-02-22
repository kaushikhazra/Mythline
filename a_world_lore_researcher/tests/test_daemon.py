"""Tests for the daemon loop — zone picking, lifecycle, signal handling, publish_fn."""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.daemon import Daemon
from src.models import ResearchCheckpoint, MessageEnvelope, MessageType


class TestPickNextZone:
    def setup_method(self):
        self.daemon = Daemon()

    def test_returns_starting_zone_when_fresh(self):
        cp = ResearchCheckpoint(zone_name="")
        result = self.daemon._pick_next_zone(cp)
        assert result == "elwynn_forest"

    def test_returns_none_when_starting_zone_completed(self):
        cp = ResearchCheckpoint(zone_name="", completed_zones=["elwynn_forest"])
        result = self.daemon._pick_next_zone(cp)
        assert result is None

    def test_resumes_in_progress_zone(self):
        cp = ResearchCheckpoint(zone_name="westfall", current_step=3)
        result = self.daemon._pick_next_zone(cp)
        assert result == "westfall"

    def test_priority_queue_first(self):
        cp = ResearchCheckpoint(
            zone_name="",
            priority_queue=["stormwind_city", "ironforge"],
            progression_queue=["westfall", "redridge"],
        )
        result = self.daemon._pick_next_zone(cp)
        assert result == "stormwind_city"

    def test_skips_completed_in_priority(self):
        cp = ResearchCheckpoint(
            zone_name="",
            priority_queue=["stormwind_city", "ironforge"],
            completed_zones=["stormwind_city"],
        )
        result = self.daemon._pick_next_zone(cp)
        assert result == "ironforge"

    def test_falls_through_to_progression(self):
        cp = ResearchCheckpoint(
            zone_name="",
            priority_queue=["stormwind_city"],
            progression_queue=["westfall"],
            completed_zones=["stormwind_city", "elwynn_forest"],
        )
        result = self.daemon._pick_next_zone(cp)
        assert result == "westfall"

    def test_skips_completed_in_progression(self):
        cp = ResearchCheckpoint(
            zone_name="",
            progression_queue=["westfall", "redridge"],
            completed_zones=["westfall", "elwynn_forest"],
        )
        result = self.daemon._pick_next_zone(cp)
        assert result == "redridge"


class TestMakePublishFn:
    @pytest.mark.asyncio
    async def test_publish_fn_sends_to_channel(self):
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


class TestDaemonLifecycle:
    @pytest.mark.asyncio
    @patch("src.daemon.save_checkpoint", new_callable=AsyncMock)
    @patch("src.daemon.run_pipeline", new_callable=AsyncMock)
    @patch("src.daemon.load_checkpoint", new_callable=AsyncMock, return_value=None)
    @patch("src.daemon.aio_pika.connect_robust", new_callable=AsyncMock)
    @patch("src.daemon.LoreResearcher")
    async def test_starts_and_runs_one_cycle(
        self, mock_researcher_cls, mock_rabbit, mock_load, mock_pipeline, mock_save
    ):
        daemon = Daemon()

        async def stop_after_pipeline(cp, researcher, publish_fn):
            daemon._running = False
            cp.completed_zones.append(cp.zone_name)
            return cp

        mock_pipeline.side_effect = stop_after_pipeline

        mock_conn = AsyncMock()
        mock_conn.channel = AsyncMock()
        mock_rabbit.return_value = mock_conn

        await daemon.start()

        mock_pipeline.assert_called_once()
        # Verify researcher and publish_fn were passed
        call_args = mock_pipeline.call_args[0]
        assert len(call_args) == 3  # checkpoint, researcher, publish_fn
        assert mock_save.call_count >= 1

    @pytest.mark.asyncio
    @patch("src.daemon.save_checkpoint", new_callable=AsyncMock)
    @patch("src.daemon.load_checkpoint", new_callable=AsyncMock)
    @patch("src.daemon.aio_pika.connect_robust", new_callable=AsyncMock)
    @patch("src.daemon.LoreResearcher")
    async def test_resumes_from_checkpoint(
        self, mock_researcher_cls, mock_rabbit, mock_load, mock_save
    ):
        existing_cp = ResearchCheckpoint(
            zone_name="westfall",
            current_step=5,
            step_data={"research_raw_content": ["some data"]},
        )
        mock_load.return_value = existing_cp

        mock_conn = AsyncMock()
        mock_conn.channel = AsyncMock()
        mock_rabbit.return_value = mock_conn

        daemon = Daemon()
        captured_checkpoints = []

        with patch("src.daemon.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
            async def stop(cp, researcher, publish_fn):
                # Snapshot before _main_loop cleanup mutates the object
                captured_checkpoints.append(cp.model_copy(deep=True))
                daemon._running = False
                cp.completed_zones.append(cp.zone_name)
                return cp

            mock_pipeline.side_effect = stop
            await daemon.start()
            cp = captured_checkpoints[0]
            assert cp.zone_name == "westfall"
            assert cp.current_step == 5, "Resume must preserve current_step"
            assert cp.step_data.get("research_raw_content") == ["some data"], \
                "Resume must preserve step_data"


class TestSignalHandling:
    def test_handle_signal_stops_daemon(self):
        daemon = Daemon()
        daemon._running = True
        daemon._handle_signal()
        assert daemon._running is False
