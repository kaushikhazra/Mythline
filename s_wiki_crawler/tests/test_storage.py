"""Tests for the storage layer — filesystem writes, sidecar metadata, change detection."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.models import CrawlResult, PageMetadata
from src.storage import (
    _url_to_record_id,
    _url_to_slug,
    store_page,
    store_page_with_change_detection,
)


# ---------------------------------------------------------------------------
# _url_to_slug
# ---------------------------------------------------------------------------


class TestUrlToSlug:
    def test_wiki_path(self):
        assert _url_to_slug("https://wowpedia.fandom.com/wiki/Hogger") == "hogger"

    def test_wiki_underscore_path(self):
        assert _url_to_slug("https://wowpedia.fandom.com/wiki/Elwynn_Forest") == "elwynn_forest"

    def test_url_encoded_spaces(self):
        assert _url_to_slug("https://example.com/wiki/Some%20Page") == "some_page"

    def test_hyphens_normalized(self):
        assert _url_to_slug("https://example.com/wiki/Loch-Modan") == "loch_modan"

    def test_nested_path(self):
        slug = _url_to_slug("https://wiki.gg/wiki/NPCs/Hogger")
        assert slug == "npcs_hogger"

    def test_no_wiki_prefix(self):
        slug = _url_to_slug("https://example.com/page/Duskwood")
        assert slug == "duskwood"

    def test_plain_path(self):
        slug = _url_to_slug("https://example.com/zones/stormwind")
        assert slug == "zones_stormwind"

    def test_empty_path_uses_hash(self):
        slug = _url_to_slug("https://example.com/")
        assert len(slug) == 16  # SHA-256 prefix fallback

    def test_special_characters_stripped(self):
        slug = _url_to_slug("https://example.com/wiki/Page_(WoW)")
        assert slug == "page_wow"

    def test_multiple_underscores_collapsed(self):
        slug = _url_to_slug("https://example.com/wiki/A___B")
        assert slug == "a_b"

    def test_w_prefix(self):
        slug = _url_to_slug("https://example.com/w/Stormwind")
        assert slug == "stormwind"


# ---------------------------------------------------------------------------
# _url_to_record_id
# ---------------------------------------------------------------------------


class TestUrlToRecordId:
    def test_deterministic(self):
        url = "https://wowpedia.fandom.com/wiki/Hogger"
        assert _url_to_record_id(url) == _url_to_record_id(url)

    def test_different_urls_different_ids(self):
        id1 = _url_to_record_id("https://wiki.com/page1")
        id2 = _url_to_record_id("https://wiki.com/page2")
        assert id1 != id2

    def test_is_16_hex_chars(self):
        record_id = _url_to_record_id("https://example.com/wiki/Test")
        assert len(record_id) == 16
        assert all(c in "0123456789abcdef" for c in record_id)


# ---------------------------------------------------------------------------
# store_page
# ---------------------------------------------------------------------------


class TestStorePage:
    @pytest.fixture
    def crawl_result(self):
        return CrawlResult(
            url="https://wowpedia.fandom.com/wiki/Hogger",
            domain="wowpedia.fandom.com",
            title="Hogger",
            content="# Hogger\n\nA famous gnoll in Elwynn Forest.",
            http_status=200,
            content_hash="abc123def456",
        )

    async def test_writes_markdown_file(self, crawl_result, tmp_path):
        with patch("src.storage.CRAWL_CACHE_ROOT", str(tmp_path)), \
             patch("src.storage.mcp_call", new_callable=AsyncMock):
            result = await store_page(crawl_result, "elwynn_forest", "wow", "npcs")

        assert result == "wow/elwynn_forest/npcs/hogger.md"
        md_path = tmp_path / "wow" / "elwynn_forest" / "npcs" / "hogger.md"
        assert md_path.exists()
        assert md_path.read_text(encoding="utf-8") == crawl_result.content

    async def test_writes_sidecar_metadata(self, crawl_result, tmp_path):
        with patch("src.storage.CRAWL_CACHE_ROOT", str(tmp_path)), \
             patch("src.storage.mcp_call", new_callable=AsyncMock):
            await store_page(crawl_result, "elwynn_forest", "wow", "npcs")

        sidecar_path = tmp_path / "wow" / "elwynn_forest" / "npcs" / "hogger.meta.json"
        assert sidecar_path.exists()
        meta = PageMetadata.model_validate_json(sidecar_path.read_text(encoding="utf-8"))
        assert meta.url == crawl_result.url
        assert meta.domain == crawl_result.domain
        assert meta.content_hash == crawl_result.content_hash
        assert meta.http_status == 200
        assert meta.content_length == len(crawl_result.content.encode("utf-8"))

    async def test_creates_graph_records(self, crawl_result, tmp_path):
        mock_mcp = AsyncMock()
        with patch("src.storage.CRAWL_CACHE_ROOT", str(tmp_path)), \
             patch("src.storage.mcp_call", mock_mcp):
            await store_page(crawl_result, "elwynn_forest", "wow", "npcs")

        # Should have 3 MCP calls: create_record, create_relation (has_page), create_relation (from_domain)
        assert mock_mcp.call_count == 3

        # First call: create_record for crawl_page
        call_args = mock_mcp.call_args_list[0]
        assert call_args[0][1] == "create_record"
        record_data = json.loads(call_args[0][2]["data"])
        assert record_data["url"] == crawl_result.url
        assert record_data["page_type"] == "npcs"

        # Second call: has_page edge
        call_args = mock_mcp.call_args_list[1]
        assert call_args[0][1] == "create_relation"
        assert call_args[0][2]["relation_type"] == "has_page"
        assert "crawl_zone:elwynn_forest" in call_args[0][2]["from_record"]

        # Third call: from_domain edge
        call_args = mock_mcp.call_args_list[2]
        assert call_args[0][1] == "create_relation"
        assert call_args[0][2]["relation_type"] == "from_domain"

    async def test_returns_none_for_no_content(self, tmp_path):
        result = CrawlResult(
            url="https://wiki.com/page", domain="wiki.com", title="",
            content=None, error="No content",
        )
        with patch("src.storage.CRAWL_CACHE_ROOT", str(tmp_path)):
            path = await store_page(result, "zone", "wow", "npcs")

        assert path is None

    async def test_creates_directory_structure(self, crawl_result, tmp_path):
        with patch("src.storage.CRAWL_CACHE_ROOT", str(tmp_path)), \
             patch("src.storage.mcp_call", new_callable=AsyncMock):
            await store_page(crawl_result, "elwynn_forest", "wow", "lore")

        assert (tmp_path / "wow" / "elwynn_forest" / "lore").is_dir()

    async def test_domain_id_dots_replaced(self, crawl_result, tmp_path):
        mock_mcp = AsyncMock()
        with patch("src.storage.CRAWL_CACHE_ROOT", str(tmp_path)), \
             patch("src.storage.mcp_call", mock_mcp):
            await store_page(crawl_result, "zone", "wow", "npcs")

        # from_domain edge should have dots replaced with underscores in domain ID
        from_domain_call = mock_mcp.call_args_list[2]
        assert "wowpedia_fandom_com" in from_domain_call[0][2]["to_record"]


# ---------------------------------------------------------------------------
# store_page_with_change_detection
# ---------------------------------------------------------------------------


class TestStorePageWithChangeDetection:
    def _make_result(self, content: str = "# Test\n\nContent.") -> CrawlResult:
        import hashlib
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        return CrawlResult(
            url="https://wiki.com/wiki/Test_Page",
            domain="wiki.com",
            title="Test Page",
            content=content,
            http_status=200,
            content_hash=content_hash,
        )

    async def test_first_write_is_always_changed(self, tmp_path):
        result = self._make_result()
        with patch("src.storage.CRAWL_CACHE_ROOT", str(tmp_path)), \
             patch("src.storage.mcp_call", new_callable=AsyncMock):
            path, changed = await store_page_with_change_detection(
                result, "zone", "wow", "lore",
            )

        assert path is not None
        assert changed is True

    async def test_same_content_not_changed(self, tmp_path):
        result = self._make_result("# Same content")
        mock_mcp = AsyncMock()

        with patch("src.storage.CRAWL_CACHE_ROOT", str(tmp_path)), \
             patch("src.storage.mcp_call", mock_mcp):
            # First write
            await store_page_with_change_detection(result, "zone", "wow", "lore")
            # Second write with same content
            path, changed = await store_page_with_change_detection(
                result, "zone", "wow", "lore",
            )

        assert changed is False
        assert path is not None

    async def test_different_content_is_changed(self, tmp_path):
        result1 = self._make_result("# Version 1")
        result2 = self._make_result("# Version 2")
        mock_mcp = AsyncMock()

        with patch("src.storage.CRAWL_CACHE_ROOT", str(tmp_path)), \
             patch("src.storage.mcp_call", mock_mcp):
            await store_page_with_change_detection(result1, "zone", "wow", "lore")
            path, changed = await store_page_with_change_detection(
                result2, "zone", "wow", "lore",
            )

        assert changed is True
        # Verify new content was written
        slug = _url_to_slug(result2.url)
        md_path = tmp_path / "wow" / "zone" / "lore" / f"{slug}.md"
        assert md_path.read_text(encoding="utf-8") == "# Version 2"

    async def test_unchanged_updates_sidecar_timestamp(self, tmp_path):
        result = self._make_result("# Stable content")
        mock_mcp = AsyncMock()

        with patch("src.storage.CRAWL_CACHE_ROOT", str(tmp_path)), \
             patch("src.storage.mcp_call", mock_mcp):
            await store_page_with_change_detection(result, "zone", "wow", "lore")

            slug = _url_to_slug(result.url)
            sidecar_path = tmp_path / "wow" / "zone" / "lore" / f"{slug}.meta.json"
            meta1 = PageMetadata.model_validate_json(sidecar_path.read_text(encoding="utf-8"))

            # Second call with same content
            await store_page_with_change_detection(result, "zone", "wow", "lore")
            meta2 = PageMetadata.model_validate_json(sidecar_path.read_text(encoding="utf-8"))

        # Timestamp should be updated even though content didn't change
        assert meta2.crawled_at >= meta1.crawled_at
        # Content hash stays the same
        assert meta2.content_hash == meta1.content_hash

    async def test_no_content_returns_none(self, tmp_path):
        result = CrawlResult(
            url="https://wiki.com/page", domain="wiki.com", title="",
            content=None, error="Failed",
        )
        with patch("src.storage.CRAWL_CACHE_ROOT", str(tmp_path)):
            path, changed = await store_page_with_change_detection(
                result, "zone", "wow", "lore",
            )

        assert path is None
        assert changed is False

    async def test_graph_updated_regardless_of_change(self, tmp_path):
        result = self._make_result("# Content")
        mock_mcp = AsyncMock()

        with patch("src.storage.CRAWL_CACHE_ROOT", str(tmp_path)), \
             patch("src.storage.mcp_call", mock_mcp):
            await store_page_with_change_detection(result, "zone", "wow", "lore")
            mock_mcp.reset_mock()

            # Same content again
            await store_page_with_change_detection(result, "zone", "wow", "lore")

        # Even though content didn't change, graph update should have been called
        assert mock_mcp.call_count == 1
        assert mock_mcp.call_args[0][1] == "update_record"
