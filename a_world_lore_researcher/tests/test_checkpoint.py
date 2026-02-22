"""Tests for checkpoint system — composite keys, budget helpers, list/scan."""

import json
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from src.checkpoint import (
    add_tokens_used,
    check_daily_budget_reset,
    delete_checkpoint,
    is_daily_budget_exhausted,
    list_checkpoints,
    load_budget,
    load_checkpoint,
    save_budget,
    save_checkpoint,
)
from src.models import BudgetState, ResearchCheckpoint


# --- Budget Helpers (now operate on BudgetState) ---


class TestBudgetReset:
    def test_reset_when_date_changes(self):
        bs = BudgetState(daily_tokens_used=10000, last_reset_date="2026-02-20")
        result = check_daily_budget_reset(bs)
        assert result.daily_tokens_used == 0
        assert result.last_reset_date == date.today().isoformat()

    def test_no_reset_same_day(self):
        today = date.today().isoformat()
        bs = BudgetState(daily_tokens_used=10000, last_reset_date=today)
        result = check_daily_budget_reset(bs)
        assert result.daily_tokens_used == 10000

    def test_reset_when_no_date_set(self):
        bs = BudgetState(daily_tokens_used=5000)
        result = check_daily_budget_reset(bs)
        assert result.daily_tokens_used == 0
        assert result.last_reset_date == date.today().isoformat()


class TestBudgetExhaustion:
    @patch("src.checkpoint.DAILY_TOKEN_BUDGET", 100_000)
    def test_not_exhausted(self):
        bs = BudgetState(daily_tokens_used=50_000)
        assert is_daily_budget_exhausted(bs) is False

    @patch("src.checkpoint.DAILY_TOKEN_BUDGET", 100_000)
    def test_exhausted(self):
        bs = BudgetState(daily_tokens_used=100_000)
        assert is_daily_budget_exhausted(bs) is True

    @patch("src.checkpoint.DAILY_TOKEN_BUDGET", 100_000)
    def test_over_budget(self):
        bs = BudgetState(daily_tokens_used=150_000)
        assert is_daily_budget_exhausted(bs) is True


class TestAddTokens:
    def test_add_tokens(self):
        bs = BudgetState(daily_tokens_used=1000)
        result = add_tokens_used(bs, 500)
        assert result.daily_tokens_used == 1500

    def test_add_tokens_accumulates(self):
        bs = BudgetState(daily_tokens_used=0)
        bs = add_tokens_used(bs, 100)
        bs = add_tokens_used(bs, 200)
        bs = add_tokens_used(bs, 300)
        assert bs.daily_tokens_used == 600


# --- Composite Key Save/Load/Delete ---


class TestSaveCheckpoint:
    @pytest.mark.asyncio
    async def test_save_calls_mcp_with_composite_key(self):
        cp = ResearchCheckpoint(job_id="job-1", zone_name="elwynn_forest", current_step=3)
        key = "world_lore_researcher:job-1:elwynn_forest"

        with patch("src.checkpoint.mcp_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"saved": f"research_state:{key}"}

            await save_checkpoint(cp, key)

            mock_call.assert_called_once()
            args = mock_call.call_args
            assert args[0][1] == "save_checkpoint"
            assert args[0][2]["agent_id"] == key


class TestLoadCheckpoint:
    @pytest.mark.asyncio
    async def test_load_returns_checkpoint(self):
        cp_data = ResearchCheckpoint(job_id="job-1", zone_name="westfall", current_step=5).model_dump()
        key = "world_lore_researcher:job-1:westfall"

        with patch("src.checkpoint.mcp_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = cp_data
            result = await load_checkpoint(key)

            assert result is not None
            assert result.zone_name == "westfall"
            assert result.current_step == 5
            assert result.job_id == "job-1"

    @pytest.mark.asyncio
    async def test_load_returns_none_when_empty(self):
        with patch("src.checkpoint.mcp_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = None
            result = await load_checkpoint("some_key")
            assert result is None

    @pytest.mark.asyncio
    async def test_load_returns_none_for_null_string(self):
        with patch("src.checkpoint.mcp_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "null"
            result = await load_checkpoint("some_key")
            assert result is None


class TestDeleteCheckpoint:
    @pytest.mark.asyncio
    async def test_delete_calls_mcp_with_key(self):
        key = "world_lore_researcher:job-1:elwynn_forest"

        with patch("src.checkpoint.mcp_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"deleted": f"research_state:{key}"}
            await delete_checkpoint(key)

            mock_call.assert_called_once()
            args = mock_call.call_args
            assert args[0][1] == "delete_checkpoint"
            assert args[0][2]["agent_id"] == key


# --- list_checkpoints ---


class TestListCheckpoints:
    @pytest.mark.asyncio
    async def test_returns_matching_keys(self):
        keys = [
            "world_lore_researcher:job-1:elwynn_forest",
            "world_lore_researcher:job-1:westfall",
        ]
        with patch("src.checkpoint.mcp_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = keys
            result = await list_checkpoints("world_lore_researcher:job-1:")
            assert result == keys

    @pytest.mark.asyncio
    async def test_returns_empty_on_none(self):
        with patch("src.checkpoint.mcp_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = None
            result = await list_checkpoints("no_match:")
            assert result == []

    @pytest.mark.asyncio
    async def test_parses_json_string_response(self):
        keys = ["key1", "key2"]
        with patch("src.checkpoint.mcp_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = json.dumps(keys)
            result = await list_checkpoints("prefix:")
            assert result == keys


# --- Budget Save/Load ---


class TestBudgetPersistence:
    @pytest.mark.asyncio
    async def test_save_budget_calls_mcp(self):
        bs = BudgetState(daily_tokens_used=25000, last_reset_date="2026-02-22")

        with patch("src.checkpoint.mcp_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"saved": "research_state:world_lore_researcher:budget"}
            await save_budget(bs)

            mock_call.assert_called_once()
            args = mock_call.call_args
            assert args[0][1] == "save_checkpoint"
            assert args[0][2]["agent_id"] == "world_lore_researcher:budget"

    @pytest.mark.asyncio
    async def test_load_budget_returns_state(self):
        bs_data = BudgetState(daily_tokens_used=10000, last_reset_date="2026-02-22").model_dump()

        with patch("src.checkpoint.mcp_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = bs_data
            result = await load_budget()

            assert result.daily_tokens_used == 10000
            assert result.last_reset_date == "2026-02-22"

    @pytest.mark.asyncio
    async def test_load_budget_returns_default_when_empty(self):
        with patch("src.checkpoint.mcp_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = None
            result = await load_budget()

            assert result.daily_tokens_used == 0
            assert result.last_reset_date == ""
