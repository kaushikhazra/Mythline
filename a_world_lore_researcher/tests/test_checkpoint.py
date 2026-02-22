"""Tests for checkpoint system — save/load logic and budget resets."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from src.checkpoint import (
    add_tokens_used,
    check_daily_budget_reset,
    is_daily_budget_exhausted,
    load_checkpoint,
    save_checkpoint,
)
from src.models import ResearchCheckpoint


class TestBudgetReset:
    def test_reset_when_date_changes(self):
        cp = ResearchCheckpoint(
            zone_name="elwynn_forest",
            daily_tokens_used=10000,
            last_reset_date="2026-02-20",
        )
        result = check_daily_budget_reset(cp)
        assert result.daily_tokens_used == 0
        assert result.last_reset_date == date.today().isoformat()

    def test_no_reset_same_day(self):
        today = date.today().isoformat()
        cp = ResearchCheckpoint(
            zone_name="elwynn_forest",
            daily_tokens_used=10000,
            last_reset_date=today,
        )
        result = check_daily_budget_reset(cp)
        assert result.daily_tokens_used == 10000

    def test_reset_when_no_date_set(self):
        cp = ResearchCheckpoint(zone_name="elwynn_forest", daily_tokens_used=5000)
        result = check_daily_budget_reset(cp)
        assert result.daily_tokens_used == 0
        assert result.last_reset_date == date.today().isoformat()


class TestBudgetExhaustion:
    @patch("src.checkpoint.DAILY_TOKEN_BUDGET", 100_000)
    def test_not_exhausted(self):
        cp = ResearchCheckpoint(zone_name="test", daily_tokens_used=50_000)
        assert is_daily_budget_exhausted(cp) is False

    @patch("src.checkpoint.DAILY_TOKEN_BUDGET", 100_000)
    def test_exhausted(self):
        cp = ResearchCheckpoint(zone_name="test", daily_tokens_used=100_000)
        assert is_daily_budget_exhausted(cp) is True

    @patch("src.checkpoint.DAILY_TOKEN_BUDGET", 100_000)
    def test_over_budget(self):
        cp = ResearchCheckpoint(zone_name="test", daily_tokens_used=150_000)
        assert is_daily_budget_exhausted(cp) is True


class TestAddTokens:
    def test_add_tokens(self):
        cp = ResearchCheckpoint(zone_name="test", daily_tokens_used=1000)
        result = add_tokens_used(cp, 500)
        assert result.daily_tokens_used == 1500

    def test_add_tokens_accumulates(self):
        cp = ResearchCheckpoint(zone_name="test", daily_tokens_used=0)
        cp = add_tokens_used(cp, 100)
        cp = add_tokens_used(cp, 200)
        cp = add_tokens_used(cp, 300)
        assert cp.daily_tokens_used == 600


class TestSaveCheckpoint:
    @pytest.mark.asyncio
    async def test_save_calls_mcp(self):
        cp = ResearchCheckpoint(zone_name="elwynn_forest", current_step=3)

        with patch("src.checkpoint.mcp_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"saved": "research_state:world_lore_researcher"}

            await save_checkpoint(cp)

            mock_call.assert_called_once()
            args = mock_call.call_args
            assert args[0][1] == "save_checkpoint"
            assert args[0][2]["agent_id"] == "world_lore_researcher"


class TestLoadCheckpoint:
    @pytest.mark.asyncio
    async def test_load_returns_checkpoint(self):
        cp_data = ResearchCheckpoint(zone_name="westfall", current_step=5).model_dump()

        with patch("src.checkpoint.mcp_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = cp_data

            result = await load_checkpoint()

            assert result is not None
            assert result.zone_name == "westfall"
            assert result.current_step == 5

    @pytest.mark.asyncio
    async def test_load_returns_none_when_empty(self):
        with patch("src.checkpoint.mcp_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = None

            result = await load_checkpoint()
            assert result is None

    @pytest.mark.asyncio
    async def test_load_returns_none_for_null_string(self):
        with patch("src.checkpoint.mcp_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "null"

            result = await load_checkpoint()
            assert result is None
