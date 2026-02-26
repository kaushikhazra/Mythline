"""Configuration — environment variables and YAML config loaders."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from src.models import CrawlScope

# ---------------------------------------------------------------------------
# Environment variables with defaults
# ---------------------------------------------------------------------------

SERVICE_ID = os.getenv("SERVICE_ID", "wiki_crawler")
GAME_NAME = os.getenv("GAME_NAME", "wow")

# RabbitMQ
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://mythline:mythline@rabbitmq:5672/")
CRAWL_JOB_QUEUE = os.getenv("CRAWL_JOB_QUEUE", "s.wiki_crawler.jobs")

# MCP Services
MCP_STORAGE_URL = os.getenv("MCP_STORAGE_URL", "http://mcp-storage:8005/mcp")
MCP_WEB_SEARCH_URL = os.getenv("MCP_WEB_SEARCH_URL", "http://mcp-web-search:8006/mcp")

# crawl4ai
CRAWL4AI_URL = os.getenv("CRAWL4AI_URL", "http://crawl4ai:11235")

# Filesystem
CRAWL_CACHE_ROOT = os.getenv("CRAWL_CACHE_ROOT", "./cache")

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "30"))
CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "3"))

# Refresh
REFRESH_INTERVAL_HOURS = int(os.getenv("REFRESH_INTERVAL_HOURS", "168"))

# Crawl limits
MAX_PAGES_PER_CATEGORY = int(os.getenv("MAX_PAGES_PER_CATEGORY", "10"))
MAX_BLOCK_RETRIES = 1


# ---------------------------------------------------------------------------
# Config file root — resolves relative to this file's package
# ---------------------------------------------------------------------------

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


# ---------------------------------------------------------------------------
# YAML config loaders
# ---------------------------------------------------------------------------

_crawl_scope_cache: CrawlScope | None = None
_sources_cache: dict | None = None


def load_crawl_scope() -> CrawlScope:
    """Load and validate crawl_scope.yml."""
    global _crawl_scope_cache
    if _crawl_scope_cache is not None:
        return _crawl_scope_cache

    config_path = _CONFIG_DIR / "crawl_scope.yml"
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    _crawl_scope_cache = CrawlScope.model_validate(raw)
    return _crawl_scope_cache


def load_sources_config() -> dict:
    """Load source tier definitions from sources.yml."""
    global _sources_cache
    if _sources_cache is not None:
        return _sources_cache

    config_path = _CONFIG_DIR / "sources.yml"
    _sources_cache = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return _sources_cache


def get_domain_tier(domain: str) -> tuple[str, float]:
    """Return (tier_name, weight) for a domain. Unknown domains get lowest tier."""
    sources = load_sources_config()
    for tier_name, tier_data in sources.get("source_tiers", {}).items():
        if domain in tier_data.get("domains", []):
            return tier_name, tier_data.get("weight", 0.5)
    return "unknown", 0.3


def get_mediawiki_api(domain: str) -> str | None:
    """Return the api.php URL for a MediaWiki domain, or None."""
    sources = load_sources_config()
    return sources.get("mediawiki_sites", {}).get(domain)


def get_all_trusted_domains() -> list[str]:
    """Return all domains from all tiers."""
    sources = load_sources_config()
    domains: list[str] = []
    for tier_data in sources.get("source_tiers", {}).values():
        domains.extend(tier_data.get("domains", []))
    return domains


def reset_config_cache() -> None:
    """Clear cached config — useful for testing."""
    global _crawl_scope_cache, _sources_cache
    _crawl_scope_cache = None
    _sources_cache = None
