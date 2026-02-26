"""Tests for Pydantic data models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.models import (
    CrawlDomainRecord,
    CrawlJob,
    CrawlPageRecord,
    CrawlResult,
    CrawlScope,
    CrawlScopeCategory,
    CrawlZoneRecord,
    PageMetadata,
    SearchResult,
)


# ---------------------------------------------------------------------------
# CrawlJob
# ---------------------------------------------------------------------------


class TestCrawlJob:
    def test_minimal(self):
        job = CrawlJob(zone_name="elwynn_forest")
        assert job.zone_name == "elwynn_forest"
        assert job.game == "wow"
        assert job.priority == 0

    def test_full(self):
        job = CrawlJob(zone_name="duskwood", game="wow", priority=5)
        assert job.game == "wow"
        assert job.priority == 5

    def test_missing_zone_name_raises(self):
        with pytest.raises(ValidationError):
            CrawlJob()

    def test_serialization_roundtrip(self):
        job = CrawlJob(zone_name="westfall", priority=3)
        data = job.model_dump()
        restored = CrawlJob.model_validate(data)
        assert restored == job

    def test_json_roundtrip(self):
        job = CrawlJob(zone_name="stormwind_city")
        json_str = job.model_dump_json()
        restored = CrawlJob.model_validate_json(json_str)
        assert restored == job

    def test_path_traversal_zone_name_rejected(self):
        with pytest.raises(ValidationError, match="Invalid path component"):
            CrawlJob(zone_name="../../../tmp/pwned")

    def test_path_traversal_backslash_rejected(self):
        with pytest.raises(ValidationError, match="Invalid path component"):
            CrawlJob(zone_name="foo\\bar")

    def test_path_traversal_slash_rejected(self):
        with pytest.raises(ValidationError, match="Invalid path component"):
            CrawlJob(zone_name="foo/bar")

    def test_path_traversal_null_byte_rejected(self):
        with pytest.raises(ValidationError, match="Invalid path component"):
            CrawlJob(zone_name="foo\x00bar")

    def test_path_traversal_game_rejected(self):
        with pytest.raises(ValidationError, match="Invalid path component"):
            CrawlJob(zone_name="elwynn_forest", game="../etc")

    def test_valid_zone_names_accepted(self):
        """Normal zone names with underscores and alphanumerics pass validation."""
        for name in ("elwynn_forest", "duskwood", "stormwind_city", "zone42"):
            job = CrawlJob(zone_name=name)
            assert job.zone_name == name


# ---------------------------------------------------------------------------
# CrawlScopeCategory / CrawlScope
# ---------------------------------------------------------------------------


class TestCrawlScope:
    def test_category_defaults(self):
        cat = CrawlScopeCategory(
            search_queries=["test {zone}"],
            preferred_domains=["example.com"],
        )
        assert cat.max_pages == 10
        assert cat.include_patterns == []
        assert cat.exclude_patterns == []

    def test_scope_from_dict(self):
        scope = CrawlScope(categories={
            "npcs": CrawlScopeCategory(
                search_queries=["site:wiki.com {zone} NPCs"],
                preferred_domains=["wiki.com"],
                max_pages=5,
            ),
        })
        assert "npcs" in scope.categories
        assert scope.categories["npcs"].max_pages == 5

    def test_empty_categories_valid(self):
        scope = CrawlScope(categories={})
        assert len(scope.categories) == 0

    def test_missing_required_fields_raises(self):
        with pytest.raises(ValidationError):
            CrawlScopeCategory(preferred_domains=["x.com"])


# ---------------------------------------------------------------------------
# PageMetadata
# ---------------------------------------------------------------------------


class TestPageMetadata:
    def test_full_metadata(self):
        now = datetime.now(timezone.utc)
        meta = PageMetadata(
            url="https://wiki.com/page",
            domain="wiki.com",
            crawled_at=now,
            content_hash="abc123",
            http_status=200,
            content_length=5000,
        )
        assert meta.url == "https://wiki.com/page"
        assert meta.content_hash == "abc123"

    def test_json_roundtrip(self):
        now = datetime.now(timezone.utc)
        meta = PageMetadata(
            url="https://wiki.com/p",
            domain="wiki.com",
            crawled_at=now,
            content_hash="hash",
            http_status=200,
            content_length=100,
        )
        json_str = meta.model_dump_json()
        restored = PageMetadata.model_validate_json(json_str)
        assert restored.url == meta.url
        assert restored.content_hash == meta.content_hash


# ---------------------------------------------------------------------------
# Graph records
# ---------------------------------------------------------------------------


class TestGraphRecords:
    def test_crawl_zone_defaults(self):
        zone = CrawlZoneRecord(name="elwynn_forest", game="wow", status="pending")
        assert zone.crawled_at is None
        assert zone.page_count == 0

    def test_crawl_page_full(self):
        now = datetime.now(timezone.utc)
        page = CrawlPageRecord(
            url="https://wiki.com/Hogger",
            title="Hogger",
            page_type="npcs",
            domain="wiki.com",
            file_path="wow/elwynn_forest/npcs/hogger.md",
            content_hash="abc",
            crawled_at=now,
            content_length=3000,
            http_status=200,
        )
        assert page.page_type == "npcs"
        assert page.file_path == "wow/elwynn_forest/npcs/hogger.md"

    def test_crawl_domain_defaults(self):
        domain = CrawlDomainRecord(name="wiki.com", tier="official")
        assert domain.consecutive_failures == 0
        assert domain.last_success is None


# ---------------------------------------------------------------------------
# Pipeline types
# ---------------------------------------------------------------------------


class TestPipelineTypes:
    def test_search_result(self):
        sr = SearchResult(
            url="https://wiki.com/page",
            title="Page",
            domain="wiki.com",
            tier="official",
            tier_weight=1.0,
        )
        assert sr.tier_weight == 1.0

    def test_crawl_result_success(self):
        cr = CrawlResult(
            url="https://wiki.com/p",
            domain="wiki.com",
            title="Test",
            content="# Hello",
            http_status=200,
            content_hash="abc",
        )
        assert cr.content is not None
        assert cr.error is None

    def test_crawl_result_failure(self):
        cr = CrawlResult(
            url="https://wiki.com/p",
            domain="wiki.com",
            title="",
            error="HTTP 500",
        )
        assert cr.content is None
        assert cr.error == "HTTP 500"

    def test_crawl_result_defaults(self):
        cr = CrawlResult(url="u", domain="d", title="t")
        assert cr.links == []
        assert cr.http_status == 0
        assert cr.content_hash == ""

    def test_crawl_result_tier_default(self):
        cr = CrawlResult(url="u", domain="d", title="t")
        assert cr.tier == "browser"

    def test_crawl_result_tier_api(self):
        cr = CrawlResult(url="u", domain="d", title="t", tier="api")
        assert cr.tier == "api"

    def test_crawl_result_tier_http(self):
        cr = CrawlResult(url="u", domain="d", title="t", tier="http")
        assert cr.tier == "http"

    def test_crawl_result_tier_in_serialization(self):
        cr = CrawlResult(url="u", domain="d", title="t", tier="api")
        data = cr.model_dump()
        assert data["tier"] == "api"
        restored = CrawlResult.model_validate(data)
        assert restored.tier == "api"
