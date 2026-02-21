"""Tests for the Web Crawler MCP server.

Uses real HTTP calls to verify content extraction works end-to-end.
These tests require internet access.
"""

import pytest

from src.server import crawl_url, crawl_urls, server


class TestCrawlUrl:
    async def test_extracts_content(self):
        """Should extract content from a real webpage."""
        result = await crawl_url("https://en.wikipedia.org/wiki/World_of_Warcraft")
        assert result["url"].startswith("http")
        assert result["content"] is not None
        assert len(result["content"]) > 100
        assert result["error"] is None

    async def test_returns_markdown(self):
        """Extracted content should be in markdown format."""
        result = await crawl_url("https://en.wikipedia.org/wiki/Python_(programming_language)")
        assert result["content"] is not None
        assert isinstance(result["content"], str)

    async def test_extracts_title(self):
        """Should extract the page title."""
        result = await crawl_url("https://en.wikipedia.org/wiki/World_of_Warcraft")
        assert result["title"] is not None
        assert len(result["title"]) > 0

    async def test_auto_adds_https(self):
        """Should add https:// prefix if missing."""
        result = await crawl_url("en.wikipedia.org/wiki/Python_(programming_language)")
        assert result["url"].startswith("https://")

    async def test_empty_url_raises_error(self):
        """Empty URL should raise ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            await crawl_url("")

    async def test_invalid_url_returns_error(self):
        """Invalid URL should return error in result dict."""
        result = await crawl_url("https://this-domain-definitely-does-not-exist-abc123.com")
        assert result["error"] is not None


class TestCrawlUrls:
    async def test_crawls_multiple_urls(self):
        """Should crawl multiple URLs concurrently."""
        urls = [
            "https://en.wikipedia.org/wiki/World_of_Warcraft",
            "https://en.wikipedia.org/wiki/Python_(programming_language)",
        ]
        results = await crawl_urls(urls)
        assert len(results) == 2
        for result in results:
            assert "url" in result
            assert "content" in result

    async def test_empty_list_raises_error(self):
        """Empty URLs list should raise ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            await crawl_urls([])


class TestServerConfiguration:
    def test_server_name(self):
        assert server.name == "Web Crawler Service"

    def test_tools_registered(self):
        tool_names = [t.name for t in server._tool_manager.list_tools()]
        assert "crawl_url" in tool_names
        assert "crawl_urls" in tool_names
