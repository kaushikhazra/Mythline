"""Tests for agent tools — crawl_webpage, helpers."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agent import ResearchContext
from src.config import CRAWL_CONTENT_TRUNCATE_CHARS
from src.models import SourceReference, SourceTier
from src.tools import crawl_webpage, make_source_ref, normalize_url


# --- normalize_url ---


class TestNormalizeUrl:
    def test_strips_trailing_slash(self):
        assert normalize_url("https://wiki.gg/page/") == "https://wiki.gg/page"

    def test_strips_fragment(self):
        assert normalize_url("https://wiki.gg/page#section") == "https://wiki.gg/page"

    def test_strips_both(self):
        assert normalize_url("https://wiki.gg/page/#section") == "https://wiki.gg/page"

    def test_no_change_needed(self):
        assert normalize_url("https://wiki.gg/page") == "https://wiki.gg/page"

    def test_preserves_query_params(self):
        assert normalize_url("https://wiki.gg/page?id=1") == "https://wiki.gg/page?id=1"

    def test_empty_fragment(self):
        assert normalize_url("https://wiki.gg/page#") == "https://wiki.gg/page"


# --- make_source_ref ---


class TestMakeSourceRef:
    def test_known_domain(self):
        ref = make_source_ref("https://wowpedia.fandom.com/wiki/Elwynn")
        assert ref.domain == "wowpedia.fandom.com"

    def test_unknown_domain_defaults_tertiary(self):
        ref = make_source_ref("https://random-blog.com/wow-guide")
        assert ref.domain == "random-blog.com"
        assert ref.tier == SourceTier.TERTIARY


# --- crawl_webpage ---


def _make_ctx(crawl_cache=None):
    """Build a mock RunContext wrapping a real ResearchContext."""
    deps = ResearchContext(crawl_cache=crawl_cache if crawl_cache is not None else {})
    ctx = MagicMock()
    ctx.deps = deps
    return ctx


class TestCrawlWebpage:
    @pytest.mark.asyncio
    async def test_crawls_url_and_captures_content(self, monkeypatch):
        ctx = _make_ctx()
        monkeypatch.setattr(
            "src.tools.rest_crawl_url",
            AsyncMock(return_value={"content": "# Page content"}),
        )

        result = await crawl_webpage(ctx, "https://wowpedia.fandom.com/wiki/Duskwood")

        assert result == "# Page content"
        assert len(ctx.deps.raw_content) == 1
        assert len(ctx.deps.sources) == 1
        assert ctx.deps.sources[0].domain == "wowpedia.fandom.com"

    @pytest.mark.asyncio
    async def test_truncates_long_content_for_agent(self, monkeypatch):
        long_content = "x" * (CRAWL_CONTENT_TRUNCATE_CHARS + 1000)
        ctx = _make_ctx()
        monkeypatch.setattr(
            "src.tools.rest_crawl_url",
            AsyncMock(return_value={"content": long_content}),
        )

        result = await crawl_webpage(ctx, "https://wiki.gg/page")

        # Agent sees truncated version
        assert len(result) < len(long_content)
        assert "[... content truncated, full version captured ...]" in result
        # Full version captured in deps
        assert ctx.deps.raw_content[0] == long_content

    @pytest.mark.asyncio
    async def test_returns_cached_on_duplicate_url(self, monkeypatch):
        cache = {"https://wiki.gg/page": "cached content"}
        ctx = _make_ctx(crawl_cache=cache)
        mock_crawl = AsyncMock()
        monkeypatch.setattr("src.tools.rest_crawl_url", mock_crawl)

        result = await crawl_webpage(ctx, "https://wiki.gg/page")

        assert result == "cached content"
        mock_crawl.assert_not_called()
        assert len(ctx.deps.raw_content) == 1

    @pytest.mark.asyncio
    async def test_dedup_normalizes_url(self, monkeypatch):
        cache = {"https://wiki.gg/page": "cached content"}
        ctx = _make_ctx(crawl_cache=cache)
        mock_crawl = AsyncMock()
        monkeypatch.setattr("src.tools.rest_crawl_url", mock_crawl)

        # Trailing slash and fragment should normalize to cached key
        result = await crawl_webpage(ctx, "https://wiki.gg/page/#section")

        assert result == "cached content"
        mock_crawl.assert_not_called()

    @pytest.mark.asyncio
    async def test_populates_cache_on_new_url(self, monkeypatch):
        cache = {}
        ctx = _make_ctx(crawl_cache=cache)
        monkeypatch.setattr(
            "src.tools.rest_crawl_url",
            AsyncMock(return_value={"content": "new content"}),
        )

        await crawl_webpage(ctx, "https://wiki.gg/new-page")

        assert "https://wiki.gg/new-page" in cache
        assert cache["https://wiki.gg/new-page"] == "new content"

    @pytest.mark.asyncio
    async def test_handles_crawl_error(self, monkeypatch):
        ctx = _make_ctx()
        monkeypatch.setattr(
            "src.tools.rest_crawl_url",
            AsyncMock(return_value={"error": "Connection timeout"}),
        )

        result = await crawl_webpage(ctx, "https://broken.com/page")

        assert "Failed to crawl" in result
        assert "Connection timeout" in result
        assert len(ctx.deps.raw_content) == 0

    @pytest.mark.asyncio
    async def test_handles_empty_content(self, monkeypatch):
        ctx = _make_ctx()
        monkeypatch.setattr(
            "src.tools.rest_crawl_url",
            AsyncMock(return_value={"content": None}),
        )

        result = await crawl_webpage(ctx, "https://empty.com/page")

        assert "Failed to crawl" in result
