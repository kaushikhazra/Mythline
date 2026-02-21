"""Tests for the daemon loop — zone picking, lifecycle, signal handling."""

from unittest.mock import AsyncMock, patch

import pytest

from src.daemon import Daemon
from src.models import ResearchCheckpoint


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


class TestDaemonLifecycle:
    @pytest.mark.asyncio
    @patch("src.daemon.save_checkpoint", new_callable=AsyncMock)
    @patch("src.daemon.run_pipeline", new_callable=AsyncMock)
    @patch("src.daemon.load_checkpoint", new_callable=AsyncMock, return_value=None)
    @patch("src.daemon.aio_pika.connect_robust", new_callable=AsyncMock)
    async def test_starts_and_runs_one_cycle(self, mock_rabbit, mock_load, mock_pipeline, mock_save):
        daemon = Daemon()

        async def stop_after_pipeline(cp):
            daemon._running = False
            cp.completed_zones.append(cp.zone_name)
            return cp

        mock_pipeline.side_effect = stop_after_pipeline

        mock_conn = AsyncMock()
        mock_conn.channel = AsyncMock()
        mock_rabbit.return_value = mock_conn

        await daemon.start()

        mock_pipeline.assert_called_once()
        assert mock_save.call_count >= 1

    @pytest.mark.asyncio
    @patch("src.daemon.save_checkpoint", new_callable=AsyncMock)
    @patch("src.daemon.load_checkpoint", new_callable=AsyncMock)
    @patch("src.daemon.aio_pika.connect_robust", new_callable=AsyncMock)
    async def test_resumes_from_checkpoint(self, mock_rabbit, mock_load, mock_save):
        existing_cp = ResearchCheckpoint(zone_name="westfall", current_step=5)
        mock_load.return_value = existing_cp

        mock_conn = AsyncMock()
        mock_conn.channel = AsyncMock()
        mock_rabbit.return_value = mock_conn

        daemon = Daemon()
        captured_zones = []

        with patch("src.daemon.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
            async def stop(cp):
                captured_zones.append(cp.zone_name)
                daemon._running = False
                cp.completed_zones.append(cp.zone_name)
                return cp

            mock_pipeline.side_effect = stop
            await daemon.start()
            assert captured_zones[0] == "westfall"


class TestSignalHandling:
    def test_handle_signal_stops_daemon(self):
        daemon = Daemon()
        daemon._running = True
        daemon._handle_signal()
        assert daemon._running is False
