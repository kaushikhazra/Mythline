"""Tests for the crawl pipeline — search, URL selection, crawling, link/zone extraction."""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, Mock, patch

import pytest

from shared.crawl import DomainThrottle
from src.crawler import (
    _extract_internal_links,
    _matches_patterns,
    _normalize_zone_slug,
    crawl_page,
    extract_connected_zones,
    select_urls,
)
from src.models import CrawlScopeCategory, SearchResult


# ---------------------------------------------------------------------------
# URL pattern matching
# ---------------------------------------------------------------------------


class TestMatchesPatterns:
    def test_no_patterns_matches_everything(self):
        assert _matches_patterns("https://wiki.com/wiki/Page", [], []) is True

    def test_exclude_blocks(self):
        assert _matches_patterns(
            "https://wiki.com/wiki/Special:Search", [], ["*/Special:*"],
        ) is False

    def test_include_requires_match(self):
        assert _matches_patterns(
            "https://wiki.com/wiki/Page", ["*/wiki/*"], [],
        ) is True

    def test_include_rejects_non_match(self):
        assert _matches_patterns(
            "https://wiki.com/other/Page", ["*/wiki/*"], [],
        ) is False

    def test_exclude_takes_priority_over_include(self):
        assert _matches_patterns(
            "https://wiki.com/wiki/User:Admin", ["*/wiki/*"], ["*/User:*"],
        ) is False

    def test_multiple_excludes(self):
        assert _matches_patterns(
            "https://wiki.com/wiki/Talk:Page", [], ["*/Special:*", "*/Talk:*"],
        ) is False


# ---------------------------------------------------------------------------
# URL selection
# ---------------------------------------------------------------------------


class TestSelectUrls:
    def _make_results(self, items: list[tuple[str, str, float]]) -> list[SearchResult]:
        return [
            SearchResult(url=url, title="", domain=domain, tier="t", tier_weight=weight)
            for url, domain, weight in items
        ]

    def test_preferred_domain_first(self):
        category = CrawlScopeCategory(
            search_queries=["q"],
            preferred_domains=["wiki.com", "other.com"],
            max_pages=10,
        )
        results = self._make_results([
            ("https://other.com/a", "other.com", 0.8),
            ("https://wiki.com/b", "wiki.com", 1.0),
            ("https://third.com/c", "third.com", 0.6),
        ])
        selected = select_urls(results, category, set())
        assert selected[0].domain == "wiki.com"
        assert selected[1].domain == "other.com"

    def test_max_pages_cap(self):
        category = CrawlScopeCategory(
            search_queries=["q"],
            preferred_domains=["wiki.com"],
            max_pages=2,
        )
        results = self._make_results([
            (f"https://wiki.com/{i}", "wiki.com", 1.0) for i in range(5)
        ])
        selected = select_urls(results, category, set())
        assert len(selected) == 2

    def test_already_crawled_excluded(self):
        category = CrawlScopeCategory(
            search_queries=["q"],
            preferred_domains=["wiki.com"],
        )
        results = self._make_results([
            ("https://wiki.com/a", "wiki.com", 1.0),
            ("https://wiki.com/b", "wiki.com", 1.0),
        ])
        selected = select_urls(results, category, {"https://wiki.com/a"})
        assert len(selected) == 1
        assert selected[0].url == "https://wiki.com/b"

    def test_exclude_patterns_applied(self):
        category = CrawlScopeCategory(
            search_queries=["q"],
            preferred_domains=["wiki.com"],
            exclude_patterns=["*/Special:*"],
        )
        results = self._make_results([
            ("https://wiki.com/wiki/Special:Search", "wiki.com", 1.0),
            ("https://wiki.com/wiki/Good_Page", "wiki.com", 1.0),
        ])
        selected = select_urls(results, category, set())
        assert len(selected) == 1
        assert "Good_Page" in selected[0].url

    def test_unknown_domain_sorted_last(self):
        category = CrawlScopeCategory(
            search_queries=["q"],
            preferred_domains=["wiki.com"],
        )
        results = self._make_results([
            ("https://random.org/p", "random.org", 0.3),
            ("https://wiki.com/p", "wiki.com", 1.0),
        ])
        selected = select_urls(results, category, set())
        assert selected[0].domain == "wiki.com"

    def test_empty_results(self):
        category = CrawlScopeCategory(
            search_queries=["q"],
            preferred_domains=["wiki.com"],
        )
        assert select_urls([], category, set()) == []


# ---------------------------------------------------------------------------
# Internal link extraction
# ---------------------------------------------------------------------------


class TestExtractInternalLinks:
    def test_dict_links(self):
        data = {
            "links": {
                "internal": [
                    {"href": "/wiki/Hogger"},
                    {"href": "/wiki/Elwynn_Forest"},
                ],
            },
        }
        links = _extract_internal_links(data, "wowpedia.fandom.com")
        assert "/wiki/Hogger" in links
        assert "/wiki/Elwynn_Forest" in links

    def test_excludes_meta_pages(self):
        data = {
            "links": {
                "internal": [
                    {"href": "/wiki/Hogger"},
                    {"href": "/wiki/Special:Search"},
                    {"href": "/wiki/User:Admin"},
                    {"href": "/wiki/Template:Zones"},
                ],
            },
        }
        links = _extract_internal_links(data, "wowpedia.fandom.com")
        assert len(links) == 1
        assert links[0] == "/wiki/Hogger"

    def test_excludes_external_domain(self):
        data = {
            "links": {
                "internal": [
                    {"href": "https://other.com/wiki/Page"},
                ],
            },
        }
        links = _extract_internal_links(data, "wowpedia.fandom.com")
        assert len(links) == 0

    def test_no_links_key(self):
        assert _extract_internal_links({}, "wiki.com") == []

    def test_string_links(self):
        data = {
            "links": {
                "internal": ["/wiki/Hogger", "/wiki/Special:X"],
            },
        }
        links = _extract_internal_links(data, "wiki.com")
        assert links == ["/wiki/Hogger"]

    def test_empty_internal(self):
        data = {"links": {"internal": []}}
        assert _extract_internal_links(data, "wiki.com") == []


# ---------------------------------------------------------------------------
# Zone slug normalization
# ---------------------------------------------------------------------------


class TestNormalizeZoneSlug:
    def test_simple(self):
        assert _normalize_zone_slug("Elwynn_Forest") == "elwynn_forest"

    def test_url_path(self):
        assert _normalize_zone_slug("/wiki/Duskwood") == "duskwood"

    def test_spaces(self):
        assert _normalize_zone_slug("Stormwind City") == "stormwind_city"

    def test_url_encoded(self):
        assert _normalize_zone_slug("Elwynn%20Forest") == "elwynn_forest"

    def test_anchor_stripped(self):
        assert _normalize_zone_slug("Elwynn_Forest#NPCs") == "elwynn_forest"

    def test_hyphens(self):
        assert _normalize_zone_slug("Loch-Modan") == "loch_modan"


# ---------------------------------------------------------------------------
# Connected zone discovery
# ---------------------------------------------------------------------------


class TestExtractConnectedZones:
    def test_adjacent_zones_section(self):
        content = """
# Elwynn Forest

## Adjacent zones

- [Westfall](/wiki/Westfall) to the west
- [Duskwood](/wiki/Duskwood) to the south
- [Stormwind City](/wiki/Stormwind_City) to the northwest

## NPCs

- Marshal Dughan
"""
        zones = extract_connected_zones(content, "elwynn_forest")
        assert "westfall" in zones
        assert "duskwood" in zones
        assert "stormwind_city" in zones
        assert "elwynn_forest" not in zones

    def test_subzones_section(self):
        content = """
## Subzones

- [Goldshire](/wiki/Goldshire)
- [Northshire Valley](/wiki/Northshire_Valley)
"""
        zones = extract_connected_zones(content, "elwynn_forest")
        assert "goldshire" in zones
        assert "northshire_valley" in zones

    def test_wikitext_links(self):
        content = """
## Adjacent Zones

- [[Westfall]] to the west
- [[Duskwood|The dark forest]] to the south
"""
        zones = extract_connected_zones(content, "elwynn_forest")
        assert "westfall" in zones
        assert "duskwood" in zones

    def test_no_zone_section(self):
        content = """
# Elwynn Forest

This is a peaceful zone with rolling hills.

## NPCs

- Marshal Dughan
"""
        zones = extract_connected_zones(content, "elwynn_forest")
        assert zones == []

    def test_deduplication(self):
        content = """
## Adjacent zones

- [Westfall](/wiki/Westfall)
- [Westfall](/wiki/Westfall)
"""
        zones = extract_connected_zones(content, "elwynn_forest")
        assert zones.count("westfall") == 1

    def test_excludes_source_zone(self):
        content = """
## Adjacent zones

- [Elwynn Forest](/wiki/Elwynn_Forest) (this zone)
- [Westfall](/wiki/Westfall)
"""
        zones = extract_connected_zones(content, "elwynn_forest")
        assert "elwynn_forest" not in zones
        assert "westfall" in zones

    def test_stops_at_next_section(self):
        content = """
## Adjacent zones

- [Westfall](/wiki/Westfall)

## History

[Duskwood](/wiki/Duskwood) was once part of the forest.
"""
        zones = extract_connected_zones(content, "elwynn_forest")
        assert "westfall" in zones
        assert "duskwood" not in zones


# ---------------------------------------------------------------------------
# crawl_page
# ---------------------------------------------------------------------------


class TestCrawlPage:
    @pytest.fixture
    def throttle(self):
        return DomainThrottle(requests_per_minute=600)

    async def test_circuit_breaker_refuses(self, throttle):
        for _ in range(3):
            throttle.report_blocked("wiki.com")

        result = await crawl_page("https://wiki.com/page", throttle)
        assert result.error is not None
        assert "Circuit breaker" in result.error
        assert result.content is None

    async def test_successful_crawl(self, throttle):
        markdown = "# Test Page\n\nSome content about [stuff](link)."
        content_hash = hashlib.sha256(markdown.encode()).hexdigest()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{
                "markdown": markdown,
                "metadata": {"title": "Test Page"},
                "links": {"internal": []},
            }],
        }

        with patch("src.crawler.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            result = await crawl_page("https://wiki.com/page", throttle, crawl4ai_url="http://fake:11235")

        assert result.content == markdown
        assert result.content_hash == content_hash
        assert result.error is None

    async def test_http_error_status(self, throttle):
        mock_response = Mock()
        mock_response.status_code = 500

        with patch("src.crawler.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            result = await crawl_page("https://wiki.com/page", throttle, crawl4ai_url="http://fake:11235")

        assert result.error == "HTTP 500"
        assert result.content is None

    async def test_empty_content(self, throttle):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"markdown": ""}]}

        with patch("src.crawler.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            result = await crawl_page("https://wiki.com/page", throttle, crawl4ai_url="http://fake:11235")

        assert result.error == "No content extracted"

    async def test_blocked_content_detected(self, throttle):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{
                "markdown": "Please verify you are human to continue.",
                "metadata": {},
                "links": {},
            }],
        }

        with patch("src.crawler.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            result = await crawl_page("https://wiki.com/page", throttle, crawl4ai_url="http://fake:11235")

        assert result.error is not None
        assert "Blocked" in result.error
