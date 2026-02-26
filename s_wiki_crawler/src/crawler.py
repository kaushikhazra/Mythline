"""Crawl pipeline — search, URL selection, page crawling, and link extraction.

This module is 100% deterministic — no LLM calls. All decisions are
algorithmic: domain tier ranking, pattern matching, regex extraction.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from fnmatch import fnmatch
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import TextContent

from shared.crawl import CrawlVerdict, DomainThrottle, detect_blocked_content
from src.config import (
    CRAWL4AI_URL,
    MAX_BLOCK_RETRIES,
    MCP_WEB_SEARCH_URL,
    get_domain_tier,
    get_mediawiki_api,
)
from src.models import CrawlResult, CrawlScopeCategory, SearchResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MCP call helper (streamable HTTP — same pattern as WLR mcp_client.py)
# ---------------------------------------------------------------------------


async def mcp_call(
    url: str,
    tool_name: str,
    arguments: dict,
    timeout: float = 30.0,
    sse_read_timeout: float = 300.0,
) -> dict | list | str | None:
    """Call a tool on a remote MCP service via StreamableHTTP."""
    try:
        async with streamablehttp_client(url, timeout=timeout, sse_read_timeout=sse_read_timeout) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)

                if result.isError:
                    texts = [b.text for b in result.content if isinstance(b, TextContent)]
                    logger.error("MCP tool %s error: %s", tool_name, " ".join(texts))
                    return None

                texts = [b.text for b in result.content if isinstance(b, TextContent)]
                if not texts:
                    return None
                if len(texts) == 1:
                    try:
                        return json.loads(texts[0])
                    except (json.JSONDecodeError, TypeError):
                        return texts[0]
                parsed = []
                for text in texts:
                    try:
                        parsed.append(json.loads(text))
                    except (json.JSONDecodeError, TypeError):
                        parsed.append(text)
                return parsed
    except Exception as exc:
        logger.error("MCP call to %s/%s failed: %s", url, tool_name, exc)
        return None


# ---------------------------------------------------------------------------
# Search phase
# ---------------------------------------------------------------------------


async def search_for_category(
    zone_name: str,
    game: str,
    category: CrawlScopeCategory,
) -> list[SearchResult]:
    """Execute search queries for a category and collect results.

    Calls Web Search MCP (DuckDuckGo) for each query template.
    Results are deduplicated by URL and enriched with domain tier info.
    """
    results: list[SearchResult] = []
    seen_urls: set[str] = set()

    for query_template in category.search_queries:
        query = query_template.format(
            zone=zone_name.replace("_", " "),
            game=game,
        )

        search_results = await mcp_call(
            MCP_WEB_SEARCH_URL,
            "search",
            {"query": query},
        )

        if not search_results:
            continue

        items = search_results if isinstance(search_results, list) else [search_results]
        for item in items:
            if not isinstance(item, dict):
                continue
            url = item.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            domain = urlparse(url).netloc
            tier, weight = get_domain_tier(domain)

            results.append(SearchResult(
                url=url,
                title=item.get("title", ""),
                domain=domain,
                tier=tier,
                tier_weight=weight,
            ))

    return results


# ---------------------------------------------------------------------------
# URL selection
# ---------------------------------------------------------------------------


def _matches_patterns(
    url: str,
    include_patterns: list[str],
    exclude_patterns: list[str],
) -> bool:
    """Check if a URL matches include/exclude patterns (fnmatch on path)."""
    path = urlparse(url).path

    # Exclude first
    for pattern in exclude_patterns:
        if fnmatch(path, pattern):
            return False

    # If include patterns are specified, URL must match at least one
    if include_patterns:
        return any(fnmatch(path, p) for p in include_patterns)

    return True


def select_urls(
    search_results: list[SearchResult],
    category: CrawlScopeCategory,
    already_crawled: set[str],
) -> list[SearchResult]:
    """Rank, filter, and cap URLs for crawling.

    Priority: preferred_domains first (in order), then by tier weight.
    Excludes URLs matching exclude_patterns, includes only include_patterns
    (if any are defined). Skips already-crawled URLs.
    """
    filtered = []
    for result in search_results:
        if result.url in already_crawled:
            continue
        if not _matches_patterns(result.url, category.include_patterns, category.exclude_patterns):
            continue
        filtered.append(result)

    def sort_key(r: SearchResult) -> tuple[int, float]:
        try:
            preferred_idx = category.preferred_domains.index(r.domain)
        except ValueError:
            preferred_idx = len(category.preferred_domains)
        return (preferred_idx, -r.tier_weight)

    filtered.sort(key=sort_key)
    return filtered[:category.max_pages]


# ---------------------------------------------------------------------------
# Tier helpers — URL parsing, HTML conversion, link extraction
# ---------------------------------------------------------------------------


def _url_to_wiki_title(url: str) -> str | None:
    """Extract MediaWiki page title from a URL.

    Handles:
      /wiki/Elwynn_Forest         -> "Elwynn_Forest"
      /wiki/Category:Zones        -> "Category:Zones"
      /w/index.php?title=Hogger   -> "Hogger"
    Returns None if the URL path doesn't match wiki conventions.
    """
    parsed = urlparse(url)

    # Standard /wiki/Title format
    if "/wiki/" in parsed.path:
        return unquote(parsed.path.split("/wiki/", 1)[1])

    # MediaWiki /w/index.php?title=Title format
    params = parse_qs(parsed.query)
    if "title" in params:
        return params["title"][0]

    return None


def _html_to_markdown(html: str) -> str:
    """Convert HTML to clean markdown using markdownify.

    Used by Tier 1 (MediaWiki API HTML) and Tier 2 (readability-extracted HTML).
    Strips scripts, styles, images, and normalizes whitespace.
    """
    if not html or not html.strip():
        return ""

    from bs4 import BeautifulSoup
    from markdownify import markdownify as md

    # Pre-process: remove tags whose content should not appear in output
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    cleaned_html = str(soup)

    markdown = md(
        cleaned_html,
        heading_style="ATX",
        strip=["img"],
    )

    # Normalize excessive blank lines
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
    return markdown


_HREF_RE = re.compile(r'<a[^>]+href=["\']([^"\']+)["\']', re.IGNORECASE)
_EXCLUDED_SEGMENTS = {"/special:", "/user:", "/talk:", "/file:", "/template:", "/category:"}


def _extract_links_from_html(html: str, base_url: str, source_domain: str) -> list[str]:
    """Extract same-domain links from raw HTML using regex.

    Uses a simple <a href="..."> regex rather than a full HTML parser
    to avoid importing BeautifulSoup as a dependency.
    """
    links = []
    for match in _HREF_RE.finditer(html):
        href = urljoin(base_url, match.group(1))
        parsed = urlparse(href)
        if parsed.netloc != source_domain:
            continue
        if any(seg in parsed.path.lower() for seg in _EXCLUDED_SEGMENTS):
            continue
        links.append(href)
    return list(dict.fromkeys(links))  # Deduplicate, preserve order


# ---------------------------------------------------------------------------
# Tier 1 — MediaWiki Action API
# ---------------------------------------------------------------------------


async def crawl_page_api(
    url: str,
    api_url: str,
    throttle: DomainThrottle,
) -> CrawlResult | None:
    """Fetch page via MediaWiki Action API. Returns None on failure (triggers fallback)."""
    domain = urlparse(url).netloc

    title = _url_to_wiki_title(url)
    if not title:
        logger.info("tier1_fallback", extra={"url": url, "reason": "no_title"})
        return None

    await throttle.wait(domain)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, params={
                "action": "parse",
                "page": title,
                "prop": "text|links|categories",
                "format": "json",
                "disabletoc": "true",
                "disableeditsection": "true",
            })

        if response.status_code != 200:
            logger.info("tier1_fallback", extra={
                "url": url, "reason": "http_status", "detail": response.status_code,
            })
            return None

        data = response.json()

        # API error (missing page, invalid title, etc.)
        if "error" in data:
            logger.warning("mediawiki_api_error", extra={
                "url": url, "error": data["error"].get("info", "unknown"),
            })
            return None

        parse_data = data["parse"]
        html_content = parse_data["text"]["*"]
        page_title = parse_data.get("title", title)

        if not html_content or not html_content.strip():
            logger.info("tier1_fallback", extra={"url": url, "reason": "empty_html"})
            return None

        # Convert HTML to markdown
        markdown = _html_to_markdown(html_content)
        if not markdown:
            logger.info("tier1_fallback", extra={"url": url, "reason": "empty_markdown"})
            return None

        # Extract links from structured API response (main namespace only)
        api_links = parse_data.get("links", [])
        links = []
        for link_info in api_links:
            ns = link_info.get("ns", -1)
            link_title = link_info.get("*", "")
            if ns == 0 and link_title:
                link_url = f"https://{domain}/wiki/{quote(link_title.replace(' ', '_'))}"
                links.append(link_url)

        throttle.report_success(domain)
        content_hash = hashlib.sha256(markdown.encode()).hexdigest()

        return CrawlResult(
            url=url, domain=domain, title=page_title,
            content=markdown, links=links,
            http_status=200, content_hash=content_hash,
            tier="api",
        )

    except httpx.HTTPError as exc:
        logger.warning("tier1_network_error", extra={"url": url, "error": str(exc)})
        return None
    except Exception as exc:
        logger.warning("tier1_unexpected_error", extra={"url": url, "error": str(exc)})
        return None


# ---------------------------------------------------------------------------
# Tier 2 — Plain HTTP + readability extraction
# ---------------------------------------------------------------------------


async def crawl_page_http(
    url: str,
    throttle: DomainThrottle,
) -> CrawlResult | None:
    """Fetch page via plain HTTP GET + readability extraction. Returns None on failure."""
    domain = urlparse(url).netloc

    await throttle.wait(domain)

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; MythlineBot/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            })

        if response.status_code != 200:
            logger.info("tier2_fallback", extra={
                "url": url, "reason": "http_status", "detail": response.status_code,
            })
            return None

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            logger.info("tier2_fallback", extra={
                "url": url, "reason": "not_html", "detail": content_type,
            })
            return None

        raw_html = response.text

        # Article extraction via readability-lxml
        from readability import Document
        doc = Document(raw_html)
        article_html = doc.summary()
        page_title = doc.title()

        if not article_html or not article_html.strip():
            logger.info("tier2_fallback", extra={"url": url, "reason": "empty_extraction"})
            return None

        # Convert extracted HTML to markdown
        markdown = _html_to_markdown(article_html)
        if not markdown:
            logger.info("tier2_fallback", extra={"url": url, "reason": "empty_markdown"})
            return None

        # Block detection
        verdict = detect_blocked_content(markdown)
        if verdict.is_blocked:
            throttle.report_blocked(domain)
            logger.info("tier2_fallback", extra={
                "url": url, "reason": "blocked", "detail": verdict.reason,
            })
            return None

        # Extract links from raw HTML (before readability strips them)
        links = _extract_links_from_html(raw_html, url, domain)

        throttle.report_success(domain)
        content_hash = hashlib.sha256(markdown.encode()).hexdigest()

        return CrawlResult(
            url=url, domain=domain, title=page_title,
            content=markdown, links=links,
            http_status=200, content_hash=content_hash,
            tier="http",
        )

    except httpx.HTTPError as exc:
        logger.warning("tier2_network_error", extra={"url": url, "error": str(exc)})
        return None
    except Exception as exc:
        logger.warning("tier2_unexpected_error", extra={"url": url, "error": str(exc)})
        return None


# ---------------------------------------------------------------------------
# Tier dispatcher — routes to best available tier
# ---------------------------------------------------------------------------


async def crawl_page(
    url: str,
    throttle: DomainThrottle,
    *,
    crawl4ai_url: str | None = None,
) -> CrawlResult:
    """Crawl a URL using the best available tier.

    Dispatch: MediaWiki API (Tier 1) -> plain HTTP (Tier 2) -> crawl4ai (Tier 3).
    Falls through tiers on failure. Circuit breaker checked once at entry.
    """
    domain = urlparse(url).netloc

    # Circuit breaker — checked once, applies to all tiers
    if throttle.is_tripped(domain):
        return CrawlResult(
            url=url, domain=domain, title="",
            error=f"Circuit breaker open for {domain}",
        )

    # Tier 1: MediaWiki API
    api_url = get_mediawiki_api(domain)
    if api_url:
        result = await crawl_page_api(url, api_url, throttle)
        if result is not None:
            return result
        logger.info("tier1_to_tier2", extra={"url": url, "domain": domain})

    # Tier 2: Plain HTTP + readability
    result = await crawl_page_http(url, throttle)
    if result is not None:
        return result
    logger.info("tier2_to_tier3", extra={"url": url, "domain": domain})

    # Tier 3: crawl4ai browser (final fallback)
    return await crawl_page_browser(url, throttle, crawl4ai_url=crawl4ai_url)


# ---------------------------------------------------------------------------
# Tier 3 — crawl4ai /crawl endpoint (browser)
# ---------------------------------------------------------------------------


async def crawl_page_browser(
    url: str,
    throttle: DomainThrottle,
    *,
    crawl4ai_url: str | None = None,
) -> CrawlResult:
    """Crawl a single URL via crawl4ai /crawl endpoint.

    1. Check circuit breaker
    2. Throttle per-domain
    3. POST to /crawl with browser stealth config
    4. Validate content (block detection)
    5. Extract internal links
    """
    base_url = crawl4ai_url or CRAWL4AI_URL
    domain = urlparse(url).netloc

    if throttle.is_tripped(domain):
        return CrawlResult(
            url=url, domain=domain, title="",
            error=f"Circuit breaker open for {domain}",
        )

    for attempt in range(MAX_BLOCK_RETRIES + 1):
        await throttle.wait(domain)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{base_url}/crawl",
                    json={
                        "urls": [url],
                        "browser_config": {
                            "headless": True,
                            "stealth_mode": True,
                            "user_agent_mode": "random",
                            "text_mode": True,
                        },
                        "crawler_config": {
                            "simulate_user": True,
                            "cache_mode": "bypass",
                            "page_timeout": 60000,
                            "wait_until": "networkidle",
                            "remove_overlay_elements": True,
                            "scan_full_page": True,
                            "score_links": True,
                        },
                    },
                )

            if response.status_code == 429:
                throttle.report_blocked(domain)
                logger.warning("HTTP 429 from crawl4ai for %s", url)
                if attempt < MAX_BLOCK_RETRIES:
                    continue
                return CrawlResult(
                    url=url, domain=domain, title="",
                    http_status=429, error="Rate limited (429)",
                )

            if response.status_code != 200:
                logger.warning("crawl4ai returned %s for %s", response.status_code, url)
                return CrawlResult(
                    url=url, domain=domain, title="",
                    http_status=response.status_code,
                    error=f"HTTP {response.status_code}",
                )

            data = response.json()

            # /crawl returns {"results": [{"markdown": ..., "metadata": ..., "links": ...}]}
            results_list = data.get("results", [])
            result_data = results_list[0] if results_list else data

            markdown = result_data.get("markdown", "")
            title = result_data.get("metadata", {}).get("title", "") if isinstance(result_data.get("metadata"), dict) else ""
            links = _extract_internal_links(result_data, domain)

            if not markdown:
                return CrawlResult(
                    url=url, domain=domain, title=title, links=links,
                    http_status=200, error="No content extracted",
                )

            # Block detection
            verdict = detect_blocked_content(markdown)
            if verdict.is_blocked:
                throttle.report_blocked(domain)
                logger.warning("Blocked content from %s: %s", url, verdict.reason)
                if attempt < MAX_BLOCK_RETRIES:
                    continue
                return CrawlResult(
                    url=url, domain=domain, title=title,
                    http_status=200, error=f"Blocked: {verdict.reason}",
                )

            throttle.report_success(domain)
            content_hash = hashlib.sha256(markdown.encode()).hexdigest()

            return CrawlResult(
                url=url, domain=domain, title=title,
                content=markdown, links=links,
                http_status=200, content_hash=content_hash,
            )

        except httpx.HTTPError as exc:
            logger.warning("crawl4ai HTTP error for %s: %s", url, exc)
            return CrawlResult(
                url=url, domain=domain, title="",
                error=str(exc),
            )
        except Exception as exc:
            logger.error("crawl4ai unexpected error for %s: %s", url, exc, exc_info=True)
            return CrawlResult(
                url=url, domain=domain, title="",
                error=str(exc),
            )

    return CrawlResult(
        url=url, domain=domain, title="",
        error="Max retries exceeded",
    )


# ---------------------------------------------------------------------------
# Link extraction
# ---------------------------------------------------------------------------


def _extract_internal_links(crawl_result_data: dict, source_domain: str) -> list[str]:
    """Extract internal wiki links from crawl4ai result.

    Filters to same-domain links, excludes Special/User/Talk pages.
    """
    links = crawl_result_data.get("links", {})
    if not isinstance(links, dict):
        return []

    internal = links.get("internal", [])
    if not isinstance(internal, list):
        return []

    _EXCLUDED_SEGMENTS = {"/special:", "/user:", "/talk:", "/file:", "/template:", "/category:"}
    valid_links: list[str] = []

    for link_info in internal:
        if isinstance(link_info, dict):
            href = link_info.get("href", "")
        elif isinstance(link_info, str):
            href = link_info
        else:
            continue

        if not href:
            continue

        parsed = urlparse(href)
        if parsed.netloc and parsed.netloc != source_domain:
            continue

        path_lower = parsed.path.lower()
        if any(seg in path_lower for seg in _EXCLUDED_SEGMENTS):
            continue

        valid_links.append(href)

    return valid_links


# ---------------------------------------------------------------------------
# Connected zone discovery (regex on markdown)
# ---------------------------------------------------------------------------

# Patterns for adjacent/connected zone sections in wiki markdown
_ZONE_SECTION_PATTERNS = [
    re.compile(r"#{2,3}\s*(?:adjacent|neighboring|connected|nearby)\s+zones?", re.IGNORECASE),
    re.compile(r"#{2,3}\s*subzones?", re.IGNORECASE),
    re.compile(r"#{2,3}\s*(?:borders?|boundaries)", re.IGNORECASE),
]

# Wiki link patterns in markdown
_WIKI_LINK_RE = re.compile(r"\[([^\]]+)\]\(/wiki/([^)]+)\)")
_WIKITEXT_LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def _normalize_zone_slug(raw: str) -> str:
    """Convert a wiki page title/path to a zone slug."""
    # Strip leading /wiki/ if present
    slug = raw.strip().lstrip("/")
    if slug.startswith("wiki/"):
        slug = slug[5:]

    # Replace URL encoding, spaces, hyphens with underscores
    slug = slug.replace("%20", "_").replace(" ", "_").replace("-", "_")
    slug = slug.lower().strip("_")

    # Remove anything after # (section anchors)
    if "#" in slug:
        slug = slug.split("#")[0]

    return slug


def extract_connected_zones(overview_content: str, source_zone: str) -> list[str]:
    """Extract connected zone names from a zone overview page.

    Looks for "Adjacent zones", "Subzones", "Borders" sections and
    extracts zone names from wiki links within those sections.
    Best-effort — returns empty list if no sections found.
    """
    connected: list[str] = []
    lines = overview_content.split("\n")

    in_zone_section = False
    for line in lines:
        # Check if we're entering a zone section
        for pattern in _ZONE_SECTION_PATTERNS:
            if pattern.search(line):
                in_zone_section = True
                break

        # Check if we've hit the next major section (exit)
        if in_zone_section and line.startswith("## ") and not any(p.search(line) for p in _ZONE_SECTION_PATTERNS):
            in_zone_section = False

        if not in_zone_section:
            continue

        # Extract zone names from wiki links
        for match in _WIKI_LINK_RE.finditer(line):
            zone_slug = _normalize_zone_slug(match.group(2))
            if zone_slug and zone_slug != source_zone:
                connected.append(zone_slug)

        for match in _WIKITEXT_LINK_RE.finditer(line):
            zone_slug = _normalize_zone_slug(match.group(1))
            if zone_slug and zone_slug != source_zone:
                connected.append(zone_slug)

    # Deduplicate, preserve order
    return list(dict.fromkeys(connected))
