"""Tests for MCP client helpers — StreamableHTTP calls, crawl4ai REST API,
block detection, and per-domain rate limiting."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mcp_client import (
    CrawlVerdict,
    DomainThrottle,
    _extract_all_text,
    _parse_result,
    crawl_url,
    detect_blocked_content,
    mcp_call,
)


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
# detect_blocked_content — Stage 1: Definitive phrases
# ---------------------------------------------------------------------------


class TestDetectBlockedDefinitive:
    """Stage 1 — a single definitive phrase triggers immediate block."""

    def test_cloudflare_captcha(self):
        content = "Please verify you are human to continue."
        verdict = detect_blocked_content(content)
        assert verdict.is_blocked
        assert "Cloudflare CAPTCHA" in verdict.reason

    def test_security_check(self):
        content = "Please complete the security check to access this page."
        verdict = detect_blocked_content(content)
        assert verdict.is_blocked

    def test_browser_check(self):
        content = "Checking your browser before accessing the website."
        verdict = detect_blocked_content(content)
        assert verdict.is_blocked

    def test_turnstile_widget(self):
        content = '<div class="cf-turnstile" data-sitekey="abc"></div>'
        verdict = detect_blocked_content(content)
        assert verdict.is_blocked

    def test_js_cookie_gate(self):
        content = "Enable JavaScript and cookies to continue browsing."
        verdict = detect_blocked_content(content)
        assert verdict.is_blocked

    def test_automated_access(self):
        content = "Automated access to this resource is not permitted."
        verdict = detect_blocked_content(content)
        assert verdict.is_blocked

    def test_google_bot_detection(self):
        content = "Our systems detected unusual traffic from your computer."
        verdict = detect_blocked_content(content)
        assert verdict.is_blocked

    def test_case_insensitive(self):
        content = "VERIFY YOU ARE HUMAN"
        verdict = detect_blocked_content(content)
        assert verdict.is_blocked


# ---------------------------------------------------------------------------
# detect_blocked_content — Stage 2: Soft signal accumulation
# ---------------------------------------------------------------------------


class TestDetectBlockedSoftSignals:
    """Stage 2 — individual soft signals don't trigger, combinations do."""

    def test_single_soft_signal_not_enough(self):
        # "cloudflare" (0.20) alone — needs wiki structure to avoid structural penalty
        content = (
            "# Wiki Infrastructure\n\n"
            "Cloudflare provides CDN services for this wiki. "
            "Pages are cached at edge locations worldwide.\n\n"
            "## Details\n\n"
            "The site has used this setup since [2019](wiki/History)."
        )
        verdict = detect_blocked_content(content)
        assert not verdict.is_blocked

    def test_two_medium_signals_trigger(self):
        # "too many requests" (0.45) + "try again later" (0.25) = 0.70 >= 0.6
        content = "Too many requests. Please try again later."
        verdict = detect_blocked_content(content)
        assert verdict.is_blocked
        assert "rate limit" in verdict.reason

    def test_cloudflare_plus_ray_id(self):
        # "cloudflare" (0.20) + "ray id" (0.30) + short content (0.30) = 0.80
        content = "Cloudflare error. Ray ID: abc123."
        verdict = detect_blocked_content(content)
        assert verdict.is_blocked

    def test_access_denied_plus_captcha(self):
        # "access denied" (0.35) + "captcha" (0.35) = 0.70
        content = "Access denied. Please solve the captcha to proceed."
        verdict = detect_blocked_content(content)
        assert verdict.is_blocked

    def test_just_below_threshold(self):
        # "just a moment" (0.35) alone — needs wiki structure to avoid structural penalty
        content = (
            "# Loading Guide\n\n"
            "Just a moment to understand the loading screen lore.\n\n"
            "## Tips\n\n"
            "The loading screen shows [zone art](wiki/Loading_Screens) "
            "and gameplay tips while the world streams in. "
            + "Additional details about the zone. " * 20
        )
        verdict = detect_blocked_content(content)
        assert not verdict.is_blocked


# ---------------------------------------------------------------------------
# detect_blocked_content — Stage 3: Structural analysis
# ---------------------------------------------------------------------------


class TestDetectBlockedStructural:
    """Stage 3 — short content without wiki structure adds to score."""

    def test_short_no_structure_plus_soft_signal(self):
        # "rate limit" (0.35) + short < 100 words (0.30) = 0.65
        content = "Rate limit exceeded."
        verdict = detect_blocked_content(content)
        assert verdict.is_blocked

    def test_short_with_headers_not_blocked(self):
        # Short but has wiki structure — structural penalty shouldn't fire
        content = "# Elwynn Forest\n\nA peaceful zone."
        verdict = detect_blocked_content(content)
        assert not verdict.is_blocked

    def test_short_with_links_not_blocked(self):
        content = "See [Stormwind](wiki/Stormwind) for details."
        verdict = detect_blocked_content(content)
        assert not verdict.is_blocked

    def test_medium_no_structure_adds_penalty(self):
        # < 300 words, no headers/links, + "captcha" (0.35) + no-structure (0.25) = 0.60
        filler = "word " * 100
        content = f"Solve the captcha to continue. {filler}"
        verdict = detect_blocked_content(content)
        assert verdict.is_blocked


# ---------------------------------------------------------------------------
# detect_blocked_content — Legitimate content (false positive prevention)
# ---------------------------------------------------------------------------


class TestDetectBlockedLegitimate:
    """Verify real wiki-like content is NOT flagged."""

    def test_normal_wiki_page(self):
        content = (
            "# Elwynn Forest\n\n"
            "Elwynn Forest is a lush woodland zone in the Eastern Kingdoms.\n\n"
            "## Geography\n\n"
            "The forest stretches south of [Stormwind City](wiki/Stormwind_City) "
            "and is home to many farms and homesteads.\n\n"
            "## Notable NPCs\n\n"
            "- Marshal Dughan — quest giver in Goldshire\n"
            "- Hogger — notorious gnoll leader\n\n"
            "## History\n\n"
            "After the First War, Elwynn Forest was rebuilt under the protection "
            "of the Kingdom of Stormwind."
        )
        verdict = detect_blocked_content(content)
        assert not verdict.is_blocked

    def test_page_mentioning_cloudflare_legitimately(self):
        content = (
            "# Web Infrastructure\n\n"
            "This wiki uses Cloudflare for CDN acceleration. "
            "The site has been served through Cloudflare since 2019.\n\n"
            "## Technical Details\n\n"
            "Pages are cached at the edge for improved performance."
        )
        verdict = detect_blocked_content(content)
        assert not verdict.is_blocked

    def test_stub_page_not_blocked(self):
        # A legitimate wiki stub — short but with structure
        content = "# Deadwind Pass\n\nStub article. [Help expand it](wiki/Help)."
        verdict = detect_blocked_content(content)
        assert not verdict.is_blocked

    def test_empty_string_not_blocked(self):
        # Empty content is handled upstream (before detection)
        verdict = detect_blocked_content("")
        assert not verdict.is_blocked


# ---------------------------------------------------------------------------
# DomainThrottle
# ---------------------------------------------------------------------------


class TestDomainThrottle:
    @pytest.mark.asyncio
    async def test_first_request_passes_immediately(self):
        throttle = DomainThrottle(requests_per_minute=30)
        start = time.monotonic()
        await throttle.wait("example.com")
        elapsed = time.monotonic() - start
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_second_same_domain_throttled(self):
        throttle = DomainThrottle(requests_per_minute=30)  # 2s interval
        await throttle.wait("example.com")
        start = time.monotonic()
        await throttle.wait("example.com")
        elapsed = time.monotonic() - start
        assert elapsed >= 1.5  # at least most of the 2s interval

    @pytest.mark.asyncio
    async def test_different_domains_not_throttled(self):
        throttle = DomainThrottle(requests_per_minute=30)
        await throttle.wait("alpha.com")
        start = time.monotonic()
        await throttle.wait("beta.com")
        elapsed = time.monotonic() - start
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_report_blocked_increases_backoff(self):
        throttle = DomainThrottle(requests_per_minute=600)  # 0.1s base interval
        throttle.report_blocked("slow.com")
        assert throttle._backoff["slow.com"] == 4.0  # 2.0 default * 2

        throttle.report_blocked("slow.com")
        assert throttle._backoff["slow.com"] == 8.0

    @pytest.mark.asyncio
    async def test_report_blocked_caps_at_30s(self):
        throttle = DomainThrottle(requests_per_minute=600)
        for _ in range(10):
            throttle.report_blocked("slow.com")
        assert throttle._backoff["slow.com"] <= 30.0

    @pytest.mark.asyncio
    async def test_report_success_clears_backoff(self):
        throttle = DomainThrottle(requests_per_minute=600)
        throttle.report_blocked("slow.com")
        assert "slow.com" in throttle._backoff

        throttle.report_success("slow.com")
        assert "slow.com" not in throttle._backoff

    @pytest.mark.asyncio
    async def test_report_success_noop_without_backoff(self):
        throttle = DomainThrottle(requests_per_minute=600)
        throttle.report_success("clean.com")  # should not raise
        assert "clean.com" not in throttle._backoff

    def test_circuit_breaker_not_tripped_below_threshold(self):
        throttle = DomainThrottle(requests_per_minute=600)
        throttle.report_blocked("slow.com")
        throttle.report_blocked("slow.com")
        assert not throttle.is_tripped("slow.com")

    def test_circuit_breaker_trips_at_threshold(self):
        throttle = DomainThrottle(requests_per_minute=600)
        for _ in range(DomainThrottle.CIRCUIT_BREAKER_THRESHOLD):
            throttle.report_blocked("slow.com")
        assert throttle.is_tripped("slow.com")

    def test_circuit_breaker_resets_on_success(self):
        throttle = DomainThrottle(requests_per_minute=600)
        for _ in range(DomainThrottle.CIRCUIT_BREAKER_THRESHOLD):
            throttle.report_blocked("slow.com")
        assert throttle.is_tripped("slow.com")

        throttle.report_success("slow.com")
        assert not throttle.is_tripped("slow.com")

    def test_is_tripped_false_for_unknown_domain(self):
        throttle = DomainThrottle(requests_per_minute=600)
        assert not throttle.is_tripped("never-seen.com")


# ---------------------------------------------------------------------------
# crawl_url — integration with throttle and block detection
# ---------------------------------------------------------------------------


def _make_mock_response(status_code: int, markdown: str = "") -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {"markdown": markdown}
    return resp


def _patch_httpx(mock_response):
    """Context manager that patches httpx.AsyncClient.post to return mock_response."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    patcher = patch("src.mcp_client.httpx.AsyncClient")
    mock_cls = patcher.start()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
    return patcher, mock_client


class TestCrawlUrl:
    @pytest.mark.asyncio
    async def test_successful_crawl(self):
        throttle = DomainThrottle(requests_per_minute=6000)
        resp = _make_mock_response(200, "# Page Content\n\nSome wiki text.")
        patcher, _ = _patch_httpx(resp)
        try:
            result = await crawl_url(
                "https://example.com/page", _throttle_override=throttle,
            )
        finally:
            patcher.stop()

        assert result["content"] == "# Page Content\n\nSome wiki text."
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_http_error_status(self):
        throttle = DomainThrottle(requests_per_minute=6000)
        resp = _make_mock_response(503)
        patcher, _ = _patch_httpx(resp)
        try:
            result = await crawl_url(
                "https://example.com/page", _throttle_override=throttle,
            )
        finally:
            patcher.stop()

        assert result["content"] is None
        assert "503" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_content(self):
        throttle = DomainThrottle(requests_per_minute=6000)
        resp = _make_mock_response(200, "")
        patcher, _ = _patch_httpx(resp)
        try:
            result = await crawl_url(
                "https://example.com/empty", _throttle_override=throttle,
            )
        finally:
            patcher.stop()

        assert result["content"] is None
        assert "No content" in result["error"]

    @pytest.mark.asyncio
    async def test_connection_error(self):
        import httpx

        throttle = DomainThrottle(requests_per_minute=6000)
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        with patch("src.mcp_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await crawl_url(
                "https://example.com/down", _throttle_override=throttle,
            )

        assert result["content"] is None
        assert result["error"] is not None

    @pytest.mark.asyncio
    async def test_http_429_retries_then_fails(self):
        throttle = DomainThrottle(requests_per_minute=6000)
        resp_429 = _make_mock_response(429)
        patcher, _ = _patch_httpx(resp_429)
        try:
            result = await crawl_url(
                "https://wiki.com/zone", _throttle_override=throttle,
            )
        finally:
            patcher.stop()

        assert result["content"] is None
        assert "429" in result["error"]
        # Backoff should have been set on the domain
        assert "wiki.com" in throttle._backoff

    @pytest.mark.asyncio
    async def test_blocked_content_retries_then_fails(self):
        throttle = DomainThrottle(requests_per_minute=6000)
        blocked_page = "Please verify you are human to continue."
        resp = _make_mock_response(200, blocked_page)
        patcher, _ = _patch_httpx(resp)
        try:
            result = await crawl_url(
                "https://wiki.com/zone", _throttle_override=throttle,
            )
        finally:
            patcher.stop()

        assert result["content"] is None
        assert "Blocked" in result["error"]
        assert "wiki.com" in throttle._backoff

    @pytest.mark.asyncio
    async def test_blocked_first_success_second(self):
        throttle = DomainThrottle(requests_per_minute=6000)
        blocked_page = "Please verify you are human to continue."
        good_page = "# Elwynn Forest\n\nA lush woodland zone."

        resp_blocked = _make_mock_response(200, blocked_page)
        resp_good = _make_mock_response(200, good_page)

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[resp_blocked, resp_good])

        with patch("src.mcp_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await crawl_url(
                "https://wiki.com/zone", _throttle_override=throttle,
            )

        assert result["content"] == good_page
        assert result["error"] is None
        # Success clears backoff
        assert "wiki.com" not in throttle._backoff

    @pytest.mark.asyncio
    async def test_circuit_breaker_refuses_immediately(self):
        throttle = DomainThrottle(requests_per_minute=6000)
        # Trip the circuit breaker
        for _ in range(DomainThrottle.CIRCUIT_BREAKER_THRESHOLD):
            throttle.report_blocked("wiki.com")

        # No HTTP call should be made — refused immediately
        result = await crawl_url(
            "https://wiki.com/zone", _throttle_override=throttle,
        )

        assert result["content"] is None
        assert "Circuit breaker" in result["error"]
        assert "different source" in result["error"]

    @pytest.mark.asyncio
    async def test_429_first_success_second(self):
        throttle = DomainThrottle(requests_per_minute=6000)
        good_page = "# Zone Data\n\nSome content here."

        resp_429 = _make_mock_response(429)
        resp_good = _make_mock_response(200, good_page)

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[resp_429, resp_good])

        with patch("src.mcp_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await crawl_url(
                "https://wiki.com/zone", _throttle_override=throttle,
            )

        assert result["content"] == good_page
        assert result["error"] is None
