"""Tests for MCP client helpers — StreamableHTTP calls and crawl4ai REST API."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mcp_client import _extract_all_text, _parse_result, crawl_url, mcp_call


class FakeTextContent:
    """Stands in for mcp.types.TextContent in tests."""
    def __init__(self, text: str):
        self.text = text


class FakeImageContent:
    """Non-text content block — should be filtered out."""
    pass


# ---------------------------------------------------------------------------
# _parse_result
# ---------------------------------------------------------------------------


class TestParseResult:
    def test_single_json_block(self):
        result = MagicMock()
        result.content = [FakeTextContent('{"key": "value"}')]
        with patch("src.mcp_client.TextContent", FakeTextContent):
            parsed = _parse_result(result)
        assert parsed == {"key": "value"}

    def test_single_plain_text_block(self):
        result = MagicMock()
        result.content = [FakeTextContent("plain text response")]
        with patch("src.mcp_client.TextContent", FakeTextContent):
            parsed = _parse_result(result)
        assert parsed == "plain text response"

    def test_multiple_json_blocks(self):
        result = MagicMock()
        result.content = [FakeTextContent('{"a": 1}'), FakeTextContent('{"b": 2}')]
        with patch("src.mcp_client.TextContent", FakeTextContent):
            parsed = _parse_result(result)
        assert parsed == [{"a": 1}, {"b": 2}]

    def test_empty_content(self):
        result = MagicMock()
        result.content = []
        parsed = _parse_result(result)
        assert parsed is None

    def test_non_text_blocks_filtered(self):
        result = MagicMock()
        result.content = [FakeImageContent(), FakeTextContent('{"x": 1}')]
        with patch("src.mcp_client.TextContent", FakeTextContent):
            parsed = _parse_result(result)
        assert parsed == {"x": 1}

    def test_mixed_json_and_plain_text_blocks(self):
        result = MagicMock()
        result.content = [FakeTextContent('{"a": 1}'), FakeTextContent("not json")]
        with patch("src.mcp_client.TextContent", FakeTextContent):
            parsed = _parse_result(result)
        assert parsed == [{"a": 1}, "not json"]


# ---------------------------------------------------------------------------
# _extract_all_text
# ---------------------------------------------------------------------------


class TestExtractAllText:
    def test_concatenates_text_blocks(self):
        result = MagicMock()
        result.content = [FakeTextContent("error A"), FakeTextContent("error B")]
        with patch("src.mcp_client.TextContent", FakeTextContent):
            text = _extract_all_text(result)
        assert text == "error A error B"

    def test_empty_content(self):
        result = MagicMock()
        result.content = []
        text = _extract_all_text(result)
        assert text == ""

    def test_filters_non_text_blocks(self):
        result = MagicMock()
        result.content = [FakeImageContent(), FakeTextContent("only this")]
        with patch("src.mcp_client.TextContent", FakeTextContent):
            text = _extract_all_text(result)
        assert text == "only this"


# ---------------------------------------------------------------------------
# mcp_call
# ---------------------------------------------------------------------------


class TestMcpCall:
    @pytest.mark.asyncio
    async def test_successful_call(self):
        mock_result = MagicMock()
        mock_result.isError = False
        mock_result.content = [FakeTextContent('{"status": "ok"}')]

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        with patch("src.mcp_client.streamablehttp_client") as mock_client, \
             patch("src.mcp_client.ClientSession", return_value=mock_session), \
             patch("src.mcp_client.TextContent", FakeTextContent):
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=(AsyncMock(), AsyncMock(), None)
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            result = await mcp_call("http://test/mcp", "test_tool", {"arg": "val"})

        assert result == {"status": "ok"}
        mock_session.call_tool.assert_awaited_once_with("test_tool", {"arg": "val"})

    @pytest.mark.asyncio
    async def test_error_returns_none(self):
        mock_result = MagicMock()
        mock_result.isError = True
        mock_result.content = [FakeTextContent("tool error")]

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        with patch("src.mcp_client.streamablehttp_client") as mock_client, \
             patch("src.mcp_client.ClientSession", return_value=mock_session), \
             patch("src.mcp_client.TextContent", FakeTextContent):
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=(AsyncMock(), AsyncMock(), None)
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            result = await mcp_call("http://test/mcp", "bad_tool", {})

        assert result is None


# ---------------------------------------------------------------------------
# crawl_url
# ---------------------------------------------------------------------------


class TestCrawlUrl:
    @pytest.mark.asyncio
    async def test_successful_crawl(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"markdown": "# Page Content"}

        with patch("src.mcp_client.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await crawl_url("https://example.com/page")

        assert result["content"] == "# Page Content"
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_http_error_status(self):
        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch("src.mcp_client.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await crawl_url("https://example.com/page")

        assert result["content"] is None
        assert "503" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_content(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"markdown": ""}

        with patch("src.mcp_client.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await crawl_url("https://example.com/empty")

        assert result["content"] is None
        assert "No content" in result["error"]

    @pytest.mark.asyncio
    async def test_connection_error(self):
        import httpx

        with patch("src.mcp_client.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await crawl_url("https://example.com/down")

        assert result["content"] is None
        assert result["error"] is not None
