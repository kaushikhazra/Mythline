"""Tests for checkpoint system — save/load logic and budget resets."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.checkpoint import (
    add_tokens_used,
    check_daily_budget_reset,
    is_daily_budget_exhausted,
    load_checkpoint,
    save_checkpoint,
    _extract_mcp_text,
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


class TestExtractMcpText:
    def test_extracts_text_content(self):
        response = {
            "result": {
                "content": [
                    {"type": "text", "text": '{"zone_name": "elwynn_forest"}'}
                ]
            }
        }
        assert _extract_mcp_text(response) == '{"zone_name": "elwynn_forest"}'

    def test_returns_none_for_empty_content(self):
        assert _extract_mcp_text({"result": {"content": []}}) is None
        assert _extract_mcp_text({"result": {}}) is None
        assert _extract_mcp_text({}) is None

    def test_skips_non_text_content(self):
        response = {
            "result": {
                "content": [
                    {"type": "image", "data": "..."},
                    {"type": "text", "text": "found"},
                ]
            }
        }
        assert _extract_mcp_text(response) == "found"


class TestSaveCheckpoint:
    @pytest.mark.asyncio
    async def test_save_sends_mcp_request(self):
        cp = ResearchCheckpoint(zone_name="elwynn_forest", current_step=3)

        mock_response = AsyncMock()
        mock_response.raise_for_status = lambda: None

        with patch("src.checkpoint.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            await save_checkpoint(cp)

            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            body = call_args.kwargs.get("json") or call_args[1].get("json")
            assert body["method"] == "tools/call"
            assert body["params"]["name"] == "save_checkpoint"


class TestLoadCheckpoint:
    @pytest.mark.asyncio
    async def test_load_returns_checkpoint(self):
        cp_data = ResearchCheckpoint(zone_name="westfall", current_step=5).model_dump_json()
        mcp_response = {
            "result": {
                "content": [{"type": "text", "text": cp_data}]
            }
        }

        mock_response = MagicMock()
        mock_response.raise_for_status = lambda: None
        mock_response.json.return_value = mcp_response

        with patch("src.checkpoint.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await load_checkpoint()

            assert result is not None
            assert result.zone_name == "westfall"
            assert result.current_step == 5

    @pytest.mark.asyncio
    async def test_load_returns_none_when_empty(self):
        mcp_response = {
            "result": {
                "content": [{"type": "text", "text": "null"}]
            }
        }

        mock_response = MagicMock()
        mock_response.raise_for_status = lambda: None
        mock_response.json.return_value = mcp_response

        with patch("src.checkpoint.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await load_checkpoint()
            assert result is None
