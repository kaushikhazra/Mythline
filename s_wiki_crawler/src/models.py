"""Pydantic data models for the Wiki Crawler service."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# RabbitMQ job message
# ---------------------------------------------------------------------------


class CrawlJob(BaseModel):
    """Incoming crawl request from the job queue."""

    zone_name: str = Field(description="Zone slug e.g., 'elwynn_forest'")
    game: str = Field(default="wow", description="Game identifier")
    priority: int = Field(default=0, description="Higher = process sooner")

    @field_validator("zone_name", "game")
    @classmethod
    def no_path_traversal(cls, v: str) -> str:
        """Reject values that could cause filesystem path traversal."""
        if ".." in v or "/" in v or "\\" in v or "\x00" in v:
            raise ValueError(f"Invalid path component: {v!r}")
        return v


# ---------------------------------------------------------------------------
# Crawl scope configuration (from crawl_scope.yml)
# ---------------------------------------------------------------------------


class CrawlScopeCategory(BaseModel):
    """One category in the crawl scope definition."""

    search_queries: list[str] = Field(description="Query templates with {zone} and {game}")
    preferred_domains: list[str] = Field(description="Priority order (highest first)")
    max_pages: int = Field(default=10, description="Max pages to crawl per category")
    include_patterns: list[str] = Field(default_factory=list, description="URL path patterns to include (fnmatch)")
    exclude_patterns: list[str] = Field(default_factory=list, description="URL path patterns to exclude (fnmatch)")


class CrawlScope(BaseModel):
    """Root of crawl_scope.yml — defines what to crawl per zone."""

    categories: dict[str, CrawlScopeCategory]


# ---------------------------------------------------------------------------
# Page metadata sidecar (.meta.json)
# ---------------------------------------------------------------------------


class PageMetadata(BaseModel):
    """Sidecar metadata for a cached markdown file."""

    url: str
    domain: str
    crawled_at: datetime
    content_hash: str = Field(description="SHA-256 hex digest")
    http_status: int
    content_length: int = Field(description="Bytes")


# ---------------------------------------------------------------------------
# SurrealDB graph records
# ---------------------------------------------------------------------------


class CrawlZoneRecord(BaseModel):
    """Zone crawl state — tracks what's been crawled, not lore content."""

    name: str
    game: str
    status: str = Field(description="pending | crawling | complete")
    crawled_at: datetime | None = None
    page_count: int = 0


class CrawlPageRecord(BaseModel):
    """Individual crawled page metadata."""

    url: str
    title: str
    page_type: str = Field(description="Category from crawl_scope.yml")
    domain: str
    file_path: str = Field(description="Relative to CRAWL_CACHE_ROOT")
    content_hash: str
    crawled_at: datetime
    content_length: int
    http_status: int


class CrawlDomainRecord(BaseModel):
    """Source domain health tracking."""

    name: str
    tier: str
    consecutive_failures: int = 0
    last_success: datetime | None = None
    last_failure: datetime | None = None


# ---------------------------------------------------------------------------
# Internal pipeline types
# ---------------------------------------------------------------------------


class SearchResult(BaseModel):
    """A single URL from web search results."""

    url: str
    title: str
    domain: str
    tier: str = Field(description="Source tier from sources.yml")
    tier_weight: float = Field(description="Numeric weight for ranking")


class CrawlResult(BaseModel):
    """Result of crawling a single URL."""

    url: str
    domain: str
    title: str
    content: str | None = Field(default=None, description="Markdown content")
    links: list[str] = Field(default_factory=list, description="Internal links extracted")
    http_status: int = 0
    content_hash: str = Field(default="", description="SHA-256 of content")
    error: str | None = None
    tier: str = Field(default="browser", description="Crawl tier used: api, http, or browser")
