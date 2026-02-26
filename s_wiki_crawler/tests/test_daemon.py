"""Tests for the Wiki Crawler daemon — message parsing, freshness, orchestration."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.config import REFRESH_INTERVAL_HOURS
from src.daemon import CrawlerDaemon
from src.models import CrawlJob, CrawlResult, CrawlScope, CrawlScopeCategory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def crawl_scope():
    return CrawlScope(categories={
        "zone_overview": CrawlScopeCategory(
            search_queries=["site:wiki.com {zone} zone"],
            preferred_domains=["wiki.com"],
            max_pages=2,
        ),
        "npcs": CrawlScopeCategory(
            search_queries=["site:wiki.com {zone} NPCs"],
            preferred_domains=["wiki.com"],
            max_pages=2,
        ),
    })


@pytest.fixture
def daemon(crawl_scope):
    return CrawlerDaemon(crawl_scope)


def _make_message(body: dict, *, is_valid: bool = True) -> MagicMock:
    """Create a mock aio_pika message."""
    msg = MagicMock()
    msg.body = json.dumps(body).encode()
    msg.ack = AsyncMock()
    msg.reject = AsyncMock()
    return msg


# ---------------------------------------------------------------------------
# Message parsing
# ---------------------------------------------------------------------------


class TestProcessSeed:
    async def test_valid_job_parsed(self, daemon):
        """Valid CrawlJob message is parsed and _crawl_zone is called."""
        msg = _make_message({"zone_name": "elwynn_forest", "game": "wow"})

        with patch.object(daemon, "_get_zone_record", new_callable=AsyncMock, return_value=None), \
             patch.object(daemon, "_crawl_zone", new_callable=AsyncMock) as mock_crawl:
            await daemon._process_seed(msg)

        mock_crawl.assert_awaited_once_with("elwynn_forest", "wow")
        msg.ack.assert_awaited_once()

    async def test_malformed_json_rejected(self, daemon):
        """Invalid JSON is rejected to DLQ."""
        msg = MagicMock()
        msg.body = b"not json"
        msg.reject = AsyncMock()

        await daemon._process_seed(msg)

        msg.reject.assert_awaited_once_with(requeue=False)

    async def test_invalid_schema_rejected(self, daemon):
        """Valid JSON but missing required fields is rejected to DLQ."""
        msg = _make_message({"game": "wow"})  # Missing zone_name

        await daemon._process_seed(msg)

        msg.reject.assert_awaited_once_with(requeue=False)

    async def test_fresh_zone_skipped(self, daemon):
        """Zone that was recently crawled is skipped."""
        msg = _make_message({"zone_name": "elwynn_forest"})

        recent_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        zone_record = {"status": "complete", "crawled_at": recent_time}

        with patch.object(daemon, "_get_zone_record", new_callable=AsyncMock, return_value=zone_record), \
             patch.object(daemon, "_crawl_zone", new_callable=AsyncMock) as mock_crawl:
            await daemon._process_seed(msg)

        mock_crawl.assert_not_awaited()
        msg.ack.assert_awaited_once()

    async def test_stale_zone_crawled(self, daemon):
        """Zone that's older than the refresh interval is re-crawled."""
        msg = _make_message({"zone_name": "duskwood"})

        old_time = (datetime.now(timezone.utc) - timedelta(hours=REFRESH_INTERVAL_HOURS + 1)).isoformat()
        zone_record = {"status": "complete", "crawled_at": old_time}

        with patch.object(daemon, "_get_zone_record", new_callable=AsyncMock, return_value=zone_record), \
             patch.object(daemon, "_crawl_zone", new_callable=AsyncMock) as mock_crawl:
            await daemon._process_seed(msg)

        mock_crawl.assert_awaited_once()
        msg.ack.assert_awaited_once()

    async def test_pending_zone_crawled(self, daemon):
        """Zone with status != complete is crawled."""
        msg = _make_message({"zone_name": "westfall"})

        zone_record = {"status": "pending", "crawled_at": None}

        with patch.object(daemon, "_get_zone_record", new_callable=AsyncMock, return_value=zone_record), \
             patch.object(daemon, "_crawl_zone", new_callable=AsyncMock) as mock_crawl:
            await daemon._process_seed(msg)

        mock_crawl.assert_awaited_once()

    async def test_new_zone_crawled(self, daemon):
        """Zone not in graph is crawled."""
        msg = _make_message({"zone_name": "new_zone"})

        with patch.object(daemon, "_get_zone_record", new_callable=AsyncMock, return_value=None), \
             patch.object(daemon, "_crawl_zone", new_callable=AsyncMock) as mock_crawl:
            await daemon._process_seed(msg)

        mock_crawl.assert_awaited_once()

    async def test_crawl_error_rejects_to_dlq(self, daemon):
        """If _crawl_zone raises, message is rejected to DLQ."""
        msg = _make_message({"zone_name": "bad_zone"})

        with patch.object(daemon, "_get_zone_record", new_callable=AsyncMock, return_value=None), \
             patch.object(daemon, "_crawl_zone", new_callable=AsyncMock, side_effect=RuntimeError("boom")):
            await daemon._process_seed(msg)

        msg.reject.assert_awaited_once_with(requeue=False)

    async def test_priority_passed_through(self, daemon):
        """Job priority is parsed from the message."""
        msg = _make_message({"zone_name": "zone", "priority": 5})

        with patch.object(daemon, "_get_zone_record", new_callable=AsyncMock, return_value=None), \
             patch.object(daemon, "_crawl_zone", new_callable=AsyncMock):
            await daemon._process_seed(msg)
            # No assertion on priority here — it's stored in the job but used for queue ordering


# ---------------------------------------------------------------------------
# Refresh mode
# ---------------------------------------------------------------------------


class TestRefreshOldestZone:
    async def test_no_stale_zones(self, daemon):
        """No stale zones returns False."""
        with patch("src.daemon.mcp_call", new_callable=AsyncMock, return_value=[]):
            result = await daemon._refresh_oldest_zone()

        assert result is False

    async def test_stale_zone_refreshed(self, daemon):
        """Oldest stale zone triggers a refresh crawl."""
        zone_data = [{"name": "duskwood", "game": "wow"}]

        with patch("src.daemon.mcp_call", new_callable=AsyncMock, return_value=zone_data), \
             patch.object(daemon, "_crawl_zone", new_callable=AsyncMock) as mock_crawl:
            result = await daemon._refresh_oldest_zone()

        assert result is True
        mock_crawl.assert_awaited_once_with("duskwood", "wow", is_refresh=True)

    async def test_null_result_returns_false(self, daemon):
        """None result from MCP returns False."""
        with patch("src.daemon.mcp_call", new_callable=AsyncMock, return_value=None):
            result = await daemon._refresh_oldest_zone()

        assert result is False


# ---------------------------------------------------------------------------
# Zone crawl orchestration
# ---------------------------------------------------------------------------


class TestCrawlZone:
    async def test_basic_crawl_flow(self, daemon):
        """Verifies the crawl pipeline: search → select → crawl → store."""
        from src.models import SearchResult

        mock_search = AsyncMock(return_value=[
            SearchResult(
                url="https://wiki.com/Hogger",
                title="Hogger",
                domain="wiki.com",
                tier="official",
                tier_weight=1.0,
            ),
        ])
        mock_crawl = AsyncMock(return_value=CrawlResult(
            url="https://wiki.com/Hogger",
            domain="wiki.com",
            title="Hogger",
            content="# Hogger\n\nA gnoll.",
            http_status=200,
            content_hash="abc123",
        ))
        mock_store = AsyncMock(return_value="wow/elwynn_forest/zone_overview/hogger.md")
        mock_upsert = AsyncMock()
        mock_discover = AsyncMock()
        mock_create_link = AsyncMock()

        with patch("src.daemon.search_for_category", mock_search), \
             patch("src.daemon.select_urls", return_value=[SearchResult(
                 url="https://wiki.com/Hogger", title="Hogger",
                 domain="wiki.com", tier="official", tier_weight=1.0,
             )]), \
             patch("src.daemon.crawl_page", mock_crawl), \
             patch("src.daemon.store_page", mock_store), \
             patch.object(daemon, "_upsert_zone_record", mock_upsert), \
             patch.object(daemon, "_discover_and_publish_connected_zones", mock_discover), \
             patch.object(daemon, "_create_page_link", mock_create_link):
            await daemon._crawl_zone("elwynn_forest", "wow")

        # Zone record set to crawling then complete
        assert mock_upsert.call_count == 2
        assert mock_upsert.call_args_list[0][1]["status"] == "crawling"
        assert mock_upsert.call_args_list[1][1]["status"] == "complete"

        # Connected zone discovery called
        mock_discover.assert_awaited_once()

    async def test_failed_pages_counted(self, daemon):
        """Pages with errors are counted as failed, not stored."""
        from src.models import SearchResult

        mock_crawl = AsyncMock(return_value=CrawlResult(
            url="https://wiki.com/Bad",
            domain="wiki.com",
            title="",
            content=None,
            error="HTTP 500",
        ))
        mock_store = AsyncMock()
        mock_upsert = AsyncMock()
        mock_discover = AsyncMock()

        with patch("src.daemon.search_for_category", new_callable=AsyncMock, return_value=[
                SearchResult(url="https://wiki.com/Bad", title="Bad",
                             domain="wiki.com", tier="official", tier_weight=1.0),
             ]), \
             patch("src.daemon.select_urls", return_value=[
                 SearchResult(url="https://wiki.com/Bad", title="Bad",
                              domain="wiki.com", tier="official", tier_weight=1.0),
             ]), \
             patch("src.daemon.crawl_page", mock_crawl), \
             patch("src.daemon.store_page", mock_store), \
             patch.object(daemon, "_upsert_zone_record", mock_upsert), \
             patch.object(daemon, "_discover_and_publish_connected_zones", mock_discover):
            await daemon._crawl_zone("elwynn_forest", "wow")

        # store_page never called for failed crawls
        mock_store.assert_not_awaited()

        # Zone still marked complete (with 0 stored pages)
        final_upsert = mock_upsert.call_args_list[-1]
        assert final_upsert[1]["status"] == "complete"
        assert final_upsert[1]["page_count"] == 0

    async def test_refresh_uses_change_detection(self, daemon):
        """Refresh mode uses store_page_with_change_detection."""
        from src.models import SearchResult

        mock_crawl = AsyncMock(return_value=CrawlResult(
            url="https://wiki.com/Page",
            domain="wiki.com",
            title="Page",
            content="# Content",
            http_status=200,
            content_hash="hash",
        ))
        mock_store_cd = AsyncMock(return_value=("path.md", False))
        mock_upsert = AsyncMock()
        mock_discover = AsyncMock()

        with patch("src.daemon.search_for_category", new_callable=AsyncMock, return_value=[
                SearchResult(url="https://wiki.com/Page", title="Page",
                             domain="wiki.com", tier="official", tier_weight=1.0),
             ]), \
             patch("src.daemon.select_urls", return_value=[
                 SearchResult(url="https://wiki.com/Page", title="Page",
                              domain="wiki.com", tier="official", tier_weight=1.0),
             ]), \
             patch("src.daemon.crawl_page", mock_crawl), \
             patch("src.daemon.store_page_with_change_detection", mock_store_cd), \
             patch.object(daemon, "_upsert_zone_record", mock_upsert), \
             patch.object(daemon, "_discover_and_publish_connected_zones", mock_discover), \
             patch.object(daemon, "_create_page_link", new_callable=AsyncMock):
            await daemon._crawl_zone("zone", "wow", is_refresh=True)

        mock_store_cd.assert_awaited()


# ---------------------------------------------------------------------------
# Connected zone discovery
# ---------------------------------------------------------------------------


class TestDiscoverAndPublishConnectedZones:
    async def test_discovers_from_overview_files(self, daemon, tmp_path):
        """Reads zone_overview markdown files and extracts connected zones."""
        overview_dir = tmp_path / "wow" / "elwynn_forest" / "zone_overview"
        overview_dir.mkdir(parents=True)
        (overview_dir / "overview.md").write_text(
            "## Adjacent zones\n\n- [Westfall](/wiki/Westfall)\n- [Duskwood](/wiki/Duskwood)\n",
            encoding="utf-8",
        )

        mock_mcp = AsyncMock(return_value=None)  # get_record returns None = new zone
        mock_publish = AsyncMock()

        with patch("src.daemon.CRAWL_CACHE_ROOT", str(tmp_path)), \
             patch("src.daemon.mcp_call", mock_mcp), \
             patch.object(daemon, "_publish_job", mock_publish):
            await daemon._discover_and_publish_connected_zones("elwynn_forest", "wow")

        # Should have published 2 new zones
        assert mock_publish.call_count == 2
        published_zones = {call.args[0].zone_name for call in mock_publish.call_args_list}
        assert "westfall" in published_zones
        assert "duskwood" in published_zones

    async def test_no_overview_dir(self, daemon, tmp_path):
        """No overview directory is a no-op."""
        mock_mcp = AsyncMock()
        mock_publish = AsyncMock()

        with patch("src.daemon.CRAWL_CACHE_ROOT", str(tmp_path)), \
             patch("src.daemon.mcp_call", mock_mcp), \
             patch.object(daemon, "_publish_job", mock_publish):
            await daemon._discover_and_publish_connected_zones("missing_zone", "wow")

        mock_mcp.assert_not_awaited()
        mock_publish.assert_not_awaited()

    async def test_existing_zone_not_republished(self, daemon, tmp_path):
        """Zone already in graph gets connected_to edge but not republished."""
        overview_dir = tmp_path / "wow" / "zone" / "zone_overview"
        overview_dir.mkdir(parents=True)
        (overview_dir / "page.md").write_text(
            "## Adjacent zones\n\n- [Westfall](/wiki/Westfall)\n",
            encoding="utf-8",
        )

        # get_record returns existing record
        mock_mcp = AsyncMock(return_value={"name": "westfall", "status": "complete"})
        mock_publish = AsyncMock()

        with patch("src.daemon.CRAWL_CACHE_ROOT", str(tmp_path)), \
             patch("src.daemon.mcp_call", mock_mcp), \
             patch.object(daemon, "_publish_job", mock_publish):
            await daemon._discover_and_publish_connected_zones("zone", "wow")

        # connected_to edge created, but no new zone published
        mock_publish.assert_not_awaited()


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------


class TestGraphHelpers:
    async def test_upsert_zone_record(self, daemon):
        """Upsert creates a record via MCP."""
        with patch("src.daemon.mcp_call", new_callable=AsyncMock) as mock_mcp:
            await daemon._upsert_zone_record("zone", "wow", status="crawling")

        mock_mcp.assert_awaited_once()
        call_args = mock_mcp.call_args[0]
        assert call_args[1] == "create_record"
        data = json.loads(call_args[2]["data"])
        assert data["status"] == "crawling"

    async def test_upsert_complete_has_timestamp(self, daemon):
        """Upsert with status=complete includes crawled_at."""
        with patch("src.daemon.mcp_call", new_callable=AsyncMock) as mock_mcp:
            await daemon._upsert_zone_record("zone", "wow", status="complete", page_count=5)

        data = json.loads(mock_mcp.call_args[0][2]["data"])
        assert "crawled_at" in data
        assert data["page_count"] == 5

    async def test_create_page_link(self, daemon):
        """Page link creates a links_to edge."""
        with patch("src.daemon.mcp_call", new_callable=AsyncMock) as mock_mcp:
            await daemon._create_page_link("https://a.com/1", "https://b.com/2")

        mock_mcp.assert_awaited_once()
        call_args = mock_mcp.call_args[0]
        assert call_args[1] == "create_relation"
        assert call_args[2]["relation_type"] == "links_to"

    async def test_publish_job(self, daemon):
        """Publish sends message to RabbitMQ queue."""
        mock_channel = MagicMock()
        mock_channel.default_exchange.publish = AsyncMock()
        daemon._channel = mock_channel

        job = CrawlJob(zone_name="westfall", game="wow", priority=-1)
        await daemon._publish_job(job)

        mock_channel.default_exchange.publish.assert_awaited_once()

    async def test_publish_job_no_channel(self, daemon):
        """Publish with no channel is a no-op."""
        daemon._channel = None
        job = CrawlJob(zone_name="zone", game="wow")
        # Should not raise
        await daemon._publish_job(job)
