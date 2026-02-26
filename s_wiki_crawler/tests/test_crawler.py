"""Tests for the crawl pipeline — search, URL selection, crawling, link/zone extraction."""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from shared.crawl import DomainThrottle
from src.crawler import (
    _extract_internal_links,
    _extract_links_from_html,
    _html_to_markdown,
    _matches_patterns,
    _normalize_zone_slug,
    _url_to_wiki_title,
    crawl_page,
    crawl_page_api,
    crawl_page_browser,
    crawl_page_http,
    extract_connected_zones,
    select_urls,
)
from src.models import CrawlResult, CrawlScopeCategory, SearchResult


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
# URL to wiki title extraction
# ---------------------------------------------------------------------------


class TestUrlToWikiTitle:
    def test_standard_wiki_path(self):
        assert _url_to_wiki_title("https://wowpedia.fandom.com/wiki/Elwynn_Forest") == "Elwynn_Forest"

    def test_category_path(self):
        assert _url_to_wiki_title("https://wowpedia.fandom.com/wiki/Category:Zones") == "Category:Zones"

    def test_encoded_path(self):
        assert _url_to_wiki_title("https://wowpedia.fandom.com/wiki/Stormwind%20City") == "Stormwind City"

    def test_index_php_title(self):
        assert _url_to_wiki_title("https://wowpedia.fandom.com/w/index.php?title=Hogger") == "Hogger"

    def test_no_wiki_path_returns_none(self):
        assert _url_to_wiki_title("https://example.com/page") is None

    def test_empty_url_returns_none(self):
        assert _url_to_wiki_title("") is None

    def test_path_with_subpage(self):
        assert _url_to_wiki_title("https://wiki.gg/wiki/Elwynn_Forest/NPCs") == "Elwynn_Forest/NPCs"


# ---------------------------------------------------------------------------
# HTML to markdown conversion
# ---------------------------------------------------------------------------


class TestHtmlToMarkdown:
    def test_heading_conversion(self):
        html = "<h1>Title</h1><h2>Subtitle</h2><p>Text</p>"
        md = _html_to_markdown(html)
        assert "# Title" in md
        assert "## Subtitle" in md
        assert "Text" in md

    def test_strips_scripts(self):
        html = "<p>Content</p><script>alert('xss')</script>"
        md = _html_to_markdown(html)
        assert "alert" not in md
        assert "Content" in md

    def test_strips_styles(self):
        html = "<style>.foo{color:red}</style><p>Content</p>"
        md = _html_to_markdown(html)
        assert "color" not in md
        assert "Content" in md

    def test_strips_images(self):
        html = '<p>Text</p><img src="foo.jpg" alt="Image">'
        md = _html_to_markdown(html)
        assert "foo.jpg" not in md
        assert "Text" in md

    def test_table_conversion(self):
        html = "<table><tr><th>Name</th><th>Level</th></tr><tr><td>Hogger</td><td>11</td></tr></table>"
        md = _html_to_markdown(html)
        assert "Name" in md
        assert "Hogger" in md

    def test_link_preserved(self):
        html = '<p><a href="/wiki/Hogger">Hogger</a> is an NPC.</p>'
        md = _html_to_markdown(html)
        assert "Hogger" in md

    def test_normalizes_blank_lines(self):
        html = "<p>A</p>\n\n\n\n\n<p>B</p>"
        md = _html_to_markdown(html)
        assert "\n\n\n" not in md

    def test_empty_html(self):
        assert _html_to_markdown("") == ""


# ---------------------------------------------------------------------------
# HTML link extraction
# ---------------------------------------------------------------------------


class TestExtractLinksFromHtml:
    def test_same_domain_links(self):
        html = '<a href="/wiki/Hogger">Hogger</a><a href="/wiki/Elwynn">Elwynn</a>'
        links = _extract_links_from_html(html, "https://wiki.com/wiki/Page", "wiki.com")
        assert len(links) == 2
        assert "https://wiki.com/wiki/Hogger" in links

    def test_excludes_other_domain(self):
        html = '<a href="https://other.com/page">External</a>'
        links = _extract_links_from_html(html, "https://wiki.com/", "wiki.com")
        assert len(links) == 0

    def test_excludes_special_pages(self):
        html = '<a href="/wiki/Special:Search">Search</a><a href="/wiki/Hogger">Hogger</a>'
        links = _extract_links_from_html(html, "https://wiki.com/", "wiki.com")
        assert len(links) == 1
        assert "Hogger" in links[0]

    def test_excludes_user_pages(self):
        html = '<a href="/wiki/User:Admin">Admin</a>'
        links = _extract_links_from_html(html, "https://wiki.com/", "wiki.com")
        assert len(links) == 0

    def test_deduplicates(self):
        html = '<a href="/wiki/Hogger">Link 1</a><a href="/wiki/Hogger">Link 2</a>'
        links = _extract_links_from_html(html, "https://wiki.com/", "wiki.com")
        assert len(links) == 1

    def test_empty_html(self):
        links = _extract_links_from_html("", "https://wiki.com/", "wiki.com")
        assert links == []

    def test_resolves_relative_urls(self):
        html = '<a href="/wiki/Test">Test</a>'
        links = _extract_links_from_html(html, "https://wiki.com/wiki/Page", "wiki.com")
        assert links[0] == "https://wiki.com/wiki/Test"


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
# Tier 1 — crawl_page_api
# ---------------------------------------------------------------------------


class TestCrawlPageApi:
    @pytest.fixture
    def throttle(self):
        return DomainThrottle(requests_per_minute=600)

    def _make_api_response(self, html="<p>Lore content</p>", title="Elwynn Forest",
                           links=None, categories=None, status_code=200, error=None):
        """Build a mock httpx response for the MediaWiki API."""
        mock_response = Mock()
        mock_response.status_code = status_code
        if error:
            mock_response.json.return_value = {"error": {"code": "missingtitle", "info": error}}
        else:
            mock_response.json.return_value = {
                "parse": {
                    "title": title,
                    "text": {"*": html},
                    "links": links or [{"ns": 0, "*": "Hogger"}, {"ns": 14, "*": "Zones"}],
                    "categories": categories or [{"*": "Eastern Kingdoms"}],
                },
            }
        return mock_response

    async def test_successful_api_crawl(self, throttle):
        mock_response = self._make_api_response()

        with patch("src.crawler.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            result = await crawl_page_api(
                "https://wowpedia.fandom.com/wiki/Elwynn_Forest",
                "https://wowpedia.fandom.com/api.php",
                throttle,
            )

        assert result is not None
        assert result.tier == "api"
        assert result.title == "Elwynn Forest"
        assert "Lore content" in result.content
        assert result.http_status == 200
        assert result.error is None
        # ns==0 link included, ns==14 excluded
        assert any("Hogger" in link for link in result.links)

    async def test_api_error_returns_none(self, throttle):
        mock_response = self._make_api_response(error="The page you specified doesn't exist.")

        with patch("src.crawler.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            result = await crawl_page_api(
                "https://wowpedia.fandom.com/wiki/Nonexistent_Page",
                "https://wowpedia.fandom.com/api.php",
                throttle,
            )

        assert result is None

    async def test_non_200_returns_none(self, throttle):
        mock_response = self._make_api_response(status_code=500)

        with patch("src.crawler.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            result = await crawl_page_api(
                "https://wowpedia.fandom.com/wiki/Elwynn_Forest",
                "https://wowpedia.fandom.com/api.php",
                throttle,
            )

        assert result is None

    async def test_no_wiki_title_returns_none(self, throttle):
        result = await crawl_page_api(
            "https://example.com/page",
            "https://example.com/api.php",
            throttle,
        )
        assert result is None

    async def test_empty_html_returns_none(self, throttle):
        mock_response = self._make_api_response(html="   ")

        with patch("src.crawler.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            result = await crawl_page_api(
                "https://wowpedia.fandom.com/wiki/Empty_Page",
                "https://wowpedia.fandom.com/api.php",
                throttle,
            )

        assert result is None

    async def test_network_error_returns_none(self, throttle):
        with patch("src.crawler.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            result = await crawl_page_api(
                "https://wowpedia.fandom.com/wiki/Elwynn_Forest",
                "https://wowpedia.fandom.com/api.php",
                throttle,
            )

        assert result is None

    async def test_links_only_main_namespace(self, throttle):
        links = [
            {"ns": 0, "*": "Hogger"},
            {"ns": 0, "*": "Goldshire"},
            {"ns": 14, "*": "Zones"},       # Category namespace — excluded
            {"ns": 10, "*": "Infobox"},     # Template namespace — excluded
            {"ns": 2, "*": "Admin"},        # User namespace — excluded
        ]
        mock_response = self._make_api_response(links=links)

        with patch("src.crawler.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            result = await crawl_page_api(
                "https://wowpedia.fandom.com/wiki/Elwynn_Forest",
                "https://wowpedia.fandom.com/api.php",
                throttle,
            )

        assert result is not None
        assert len(result.links) == 2  # Only Hogger and Goldshire


# ---------------------------------------------------------------------------
# Tier 2 — crawl_page_http
# ---------------------------------------------------------------------------


class TestCrawlPageHttp:
    @pytest.fixture
    def throttle(self):
        return DomainThrottle(requests_per_minute=600)

    def _make_http_response(self, html="<html><body><h1>Title</h1><p>Article content here.</p></body></html>",
                            status_code=200, content_type="text/html; charset=utf-8"):
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.headers = {"content-type": content_type}
        mock_response.text = html
        return mock_response

    async def test_successful_http_crawl(self, throttle):
        html = "<html><body><h1>Elwynn Forest</h1><p>A peaceful zone with rolling green hills.</p></body></html>"
        mock_response = self._make_http_response(html=html)

        with patch("src.crawler.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            result = await crawl_page_http("https://wiki.com/wiki/Page", throttle)

        assert result is not None
        assert result.tier == "http"
        assert result.http_status == 200
        assert result.error is None

    async def test_non_200_returns_none(self, throttle):
        mock_response = self._make_http_response(status_code=404)

        with patch("src.crawler.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            result = await crawl_page_http("https://wiki.com/wiki/Page", throttle)

        assert result is None

    async def test_non_html_returns_none(self, throttle):
        mock_response = self._make_http_response(content_type="application/json")

        with patch("src.crawler.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            result = await crawl_page_http("https://wiki.com/wiki/Page", throttle)

        assert result is None

    async def test_blocked_content_returns_none(self, throttle):
        html = "<html><body><p>Please verify you are human to continue.</p></body></html>"
        mock_response = self._make_http_response(html=html)

        with patch("src.crawler.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            result = await crawl_page_http("https://wiki.com/wiki/Page", throttle)

        assert result is None

    async def test_network_error_returns_none(self, throttle):
        with patch("src.crawler.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            result = await crawl_page_http("https://wiki.com/wiki/Page", throttle)

        assert result is None

    async def test_extracts_links_from_raw_html(self, throttle):
        # Readability needs substantial content to extract — short HTML gets discarded
        html = """<html><head><title>Elwynn Forest</title></head><body>
        <div id="content"><h1>Elwynn Forest</h1>
        <p>Elwynn Forest is a peaceful zone in the Eastern Kingdoms. It is home to the
        human city of Stormwind. The forest is dotted with farms and small settlements.</p>
        <p>Notable locations include <a href="/wiki/Hogger">Hogger's camp</a> near the
        river and the town of <a href="/wiki/Goldshire">Goldshire</a> on the main road.</p>
        <p>The zone is bordered by Westfall to the west and Duskwood to the south. Many
        adventurers begin their journey here, learning the basics of combat and exploration.</p>
        </div></body></html>"""
        mock_response = self._make_http_response(html=html)

        with patch("src.crawler.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            result = await crawl_page_http("https://wiki.com/wiki/Page", throttle)

        assert result is not None
        assert len(result.links) >= 2


# ---------------------------------------------------------------------------
# crawl_page (Tier 3 browser — renamed from original crawl_page)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Tier dispatcher — crawl_page()
# ---------------------------------------------------------------------------


class TestCrawlPageDispatcher:
    @pytest.fixture
    def throttle(self):
        return DomainThrottle(requests_per_minute=600)

    async def test_routes_to_tier1_for_mediawiki_domain(self, throttle):
        """MediaWiki domain routes to Tier 1 and returns without hitting Tier 2/3."""
        tier1_result = CrawlResult(
            url="https://wowpedia.fandom.com/wiki/Hogger",
            domain="wowpedia.fandom.com", title="Hogger",
            content="# Hogger", tier="api", http_status=200,
            content_hash="abc",
        )

        with patch("src.crawler.crawl_page_api", new_callable=AsyncMock, return_value=tier1_result) as mock_api, \
             patch("src.crawler.crawl_page_http", new_callable=AsyncMock) as mock_http, \
             patch("src.crawler.crawl_page_browser", new_callable=AsyncMock) as mock_browser:

            result = await crawl_page("https://wowpedia.fandom.com/wiki/Hogger", throttle)

        assert result.tier == "api"
        mock_api.assert_called_once()
        mock_http.assert_not_called()
        mock_browser.assert_not_called()

    async def test_tier1_failure_falls_to_tier2(self, throttle):
        """When Tier 1 returns None, dispatcher tries Tier 2."""
        tier2_result = CrawlResult(
            url="https://wowpedia.fandom.com/wiki/Hogger",
            domain="wowpedia.fandom.com", title="Hogger",
            content="# Hogger", tier="http", http_status=200,
            content_hash="abc",
        )

        with patch("src.crawler.crawl_page_api", new_callable=AsyncMock, return_value=None), \
             patch("src.crawler.crawl_page_http", new_callable=AsyncMock, return_value=tier2_result) as mock_http, \
             patch("src.crawler.crawl_page_browser", new_callable=AsyncMock) as mock_browser:

            result = await crawl_page("https://wowpedia.fandom.com/wiki/Hogger", throttle)

        assert result.tier == "http"
        mock_http.assert_called_once()
        mock_browser.assert_not_called()

    async def test_tier2_failure_falls_to_tier3(self, throttle):
        """When Tier 2 returns None, dispatcher falls to Tier 3."""
        tier3_result = CrawlResult(
            url="https://example.com/page",
            domain="example.com", title="Page",
            content="# Page", tier="browser", http_status=200,
            content_hash="abc",
        )

        with patch("src.crawler.crawl_page_http", new_callable=AsyncMock, return_value=None), \
             patch("src.crawler.crawl_page_browser", new_callable=AsyncMock, return_value=tier3_result) as mock_browser:

            result = await crawl_page("https://example.com/page", throttle)

        assert result.tier == "browser"
        mock_browser.assert_called_once()

    async def test_non_mediawiki_skips_tier1(self, throttle):
        """Non-MediaWiki domain skips Tier 1, goes to Tier 2."""
        tier2_result = CrawlResult(
            url="https://icy-veins.com/guide",
            domain="icy-veins.com", title="Guide",
            content="# Guide", tier="http", http_status=200,
            content_hash="abc",
        )

        with patch("src.crawler.crawl_page_api", new_callable=AsyncMock) as mock_api, \
             patch("src.crawler.crawl_page_http", new_callable=AsyncMock, return_value=tier2_result):

            result = await crawl_page("https://icy-veins.com/guide", throttle)

        assert result.tier == "http"
        mock_api.assert_not_called()

    async def test_circuit_breaker_blocks_all_tiers(self, throttle):
        """Circuit breaker at entry blocks before any tier is tried."""
        for _ in range(3):
            throttle.report_blocked("wiki.com")

        with patch("src.crawler.crawl_page_api", new_callable=AsyncMock) as mock_api, \
             patch("src.crawler.crawl_page_http", new_callable=AsyncMock) as mock_http, \
             patch("src.crawler.crawl_page_browser", new_callable=AsyncMock) as mock_browser:

            result = await crawl_page("https://wiki.com/page", throttle)

        assert result.error is not None
        assert "Circuit breaker" in result.error
        mock_api.assert_not_called()
        mock_http.assert_not_called()
        mock_browser.assert_not_called()

    async def test_full_fallback_chain(self, throttle):
        """All tiers fail in sequence: Tier 1 -> Tier 2 -> Tier 3."""
        tier3_result = CrawlResult(
            url="https://wowpedia.fandom.com/wiki/Hogger",
            domain="wowpedia.fandom.com", title="",
            error="HTTP 500", tier="browser",
        )

        with patch("src.crawler.crawl_page_api", new_callable=AsyncMock, return_value=None), \
             patch("src.crawler.crawl_page_http", new_callable=AsyncMock, return_value=None), \
             patch("src.crawler.crawl_page_browser", new_callable=AsyncMock, return_value=tier3_result):

            result = await crawl_page("https://wowpedia.fandom.com/wiki/Hogger", throttle)

        assert result.tier == "browser"
        assert result.error == "HTTP 500"


# ---------------------------------------------------------------------------
# crawl_page_browser (Tier 3)
# ---------------------------------------------------------------------------


class TestCrawlPageBrowser:
    @pytest.fixture
    def throttle(self):
        return DomainThrottle(requests_per_minute=600)

    async def test_circuit_breaker_refuses(self, throttle):
        for _ in range(3):
            throttle.report_blocked("wiki.com")

        result = await crawl_page_browser("https://wiki.com/page", throttle)
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

            result = await crawl_page_browser("https://wiki.com/page", throttle, crawl4ai_url="http://fake:11235")

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

            result = await crawl_page_browser("https://wiki.com/page", throttle, crawl4ai_url="http://fake:11235")

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

            result = await crawl_page_browser("https://wiki.com/page", throttle, crawl4ai_url="http://fake:11235")

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

            result = await crawl_page_browser("https://wiki.com/page", throttle, crawl4ai_url="http://fake:11235")

        assert result.error is not None
        assert "Blocked" in result.error
