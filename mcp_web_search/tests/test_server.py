"""Tests for the Web Search MCP server.

Uses real DuckDuckGo API calls to verify integration works end-to-end.
These tests require internet access.
"""

import pytest

from src.server import search, search_news, server


class TestSearch:
    async def test_returns_results(self):
        """Basic search should return a non-empty list of results."""
        results = await search("World of Warcraft Elwynn Forest")
        assert isinstance(results, list)
        assert len(results) > 0

    async def test_result_structure(self):
        """Each result should have title, url, and snippet fields."""
        results = await search("Python programming language", max_results=3)
        for result in results:
            assert "title" in result
            assert "url" in result
            assert "snippet" in result
            assert isinstance(result["title"], str)
            assert isinstance(result["url"], str)
            assert result["url"].startswith("http")

    async def test_max_results_limit(self):
        """Should respect max_results parameter."""
        results = await search("World of Warcraft", max_results=3)
        assert len(results) <= 3

    async def test_empty_query_raises_error(self):
        """Empty query should raise ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            await search("")

    async def test_whitespace_query_raises_error(self):
        """Whitespace-only query should raise ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            await search("   ")


class TestSearchNews:
    async def test_returns_news_results(self):
        """News search should return results."""
        results = await search_news("World of Warcraft", max_results=3)
        assert isinstance(results, list)
        assert len(results) > 0

    async def test_news_result_structure(self):
        """News results should have expected fields."""
        results = await search_news("gaming news", max_results=3)
        for result in results:
            assert "title" in result
            assert "url" in result
            assert "snippet" in result
            assert "date" in result
            assert "source" in result


class TestServerConfiguration:
    def test_server_name(self):
        assert server.name == "Web Search Service"

    def test_tools_registered(self):
        tool_names = [t.name for t in server._tool_manager.list_tools()]
        assert "search" in tool_names
        assert "search_news" in tool_names
