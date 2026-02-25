"""Pydantic AI tools — custom tool functions registered on agents.

Tools are standalone async functions with the pydantic-ai RunContext signature.
They are registered on Agent instances in agent.py via agent.tool().
"""

from __future__ import annotations

from urllib.parse import urlparse

from pydantic_ai import RunContext

from src.config import CRAWL_CONTENT_TRUNCATE_CHARS, get_source_tier_for_domain
from src.mcp_client import crawl_url as rest_crawl_url
from src.models import SourceReference, SourceTier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def normalize_url(url: str) -> str:
    """Normalize a URL for cache dedup: strip fragments then trailing slashes."""
    return url.split("#")[0].rstrip("/")


def make_source_ref(url: str) -> SourceReference:
    """Build a SourceReference from a URL, looking up the domain's trust tier."""
    domain = urlparse(url).netloc
    tier_name = get_source_tier_for_domain(domain)
    try:
        tier = SourceTier(tier_name) if tier_name else SourceTier.TERTIARY
    except ValueError:
        tier = SourceTier.TERTIARY
    return SourceReference(url=url, domain=domain, tier=tier)


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------


async def crawl_webpage(ctx: RunContext, url: str) -> str:
    """Crawl a URL and extract its full content as markdown.

    Use this after finding interesting URLs via web search to get
    the complete page content for lore extraction.
    """
    cache_key = normalize_url(url)
    crawl_cache = ctx.deps.crawl_cache

    if cache_key in crawl_cache:
        content = crawl_cache[cache_key]
        ctx.deps.raw_content.append(content)
        ctx.deps.sources.append(make_source_ref(url))
        truncated = content[:CRAWL_CONTENT_TRUNCATE_CHARS]
        if len(content) > CRAWL_CONTENT_TRUNCATE_CHARS:
            return truncated + "\n\n[... cached, full version captured ...]"
        return content

    result = await rest_crawl_url(url)
    content = result.get("content")
    if content:
        crawl_cache[cache_key] = content
        ctx.deps.raw_content.append(content)
        ctx.deps.sources.append(make_source_ref(url))
        if len(content) > CRAWL_CONTENT_TRUNCATE_CHARS:
            return content[:CRAWL_CONTENT_TRUNCATE_CHARS] + "\n\n[... content truncated, full version captured ...]"
        return content
    error = result.get("error", "unknown error")
    return f"Failed to crawl {url}: {error}"
