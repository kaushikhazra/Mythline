"""Centralized configuration for the World Lore Researcher agent.

All environment variables, tunable constants, and config file loaders
live here. No other module defines configuration values.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml


AGENT_DIR = Path(__file__).parent.parent


def _int_env(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


# --- Agent Identity ---

AGENT_ID = os.getenv("AGENT_ID", "world_lore_researcher")
AGENT_ROLE = os.getenv("AGENT_ROLE", "world_lore_researcher")
GAME_NAME = os.getenv("GAME_NAME", "wow")

# --- Token Budgets ---

DAILY_TOKEN_BUDGET = _int_env("DAILY_TOKEN_BUDGET", 500_000)
PER_ZONE_TOKEN_BUDGET = _int_env("PER_ZONE_TOKEN_BUDGET", 50_000)

# --- Limits ---

MAX_RESEARCH_VALIDATE_ITERATIONS = _int_env("MAX_RESEARCH_VALIDATE_ITERATIONS", 3)
RATE_LIMIT_REQUESTS_PER_MINUTE = _int_env("RATE_LIMIT_REQUESTS_PER_MINUTE", 30)
EXTRACT_CONTENT_CHAR_LIMIT = _int_env("EXTRACT_CONTENT_CHAR_LIMIT", 300_000)
CRAWL_CONTENT_TRUNCATE_CHARS = _int_env("CRAWL_CONTENT_TRUNCATE_CHARS", 5_000)

# --- Queue Names ---

JOB_QUEUE = os.getenv("JOB_QUEUE", "agent.world_lore_researcher.jobs")
STATUS_QUEUE = os.getenv("STATUS_QUEUE", "agent.world_lore_researcher.status")
VALIDATOR_QUEUE = os.getenv("VALIDATOR_QUEUE", "agent.world_lore_validator")

# --- Service URLs ---

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://mythline:mythline@localhost:5672/")
MCP_STORAGE_URL = os.getenv("MCP_STORAGE_URL", "http://localhost:8005/mcp")
MCP_WEB_SEARCH_URL = os.getenv("MCP_WEB_SEARCH_URL", "http://localhost:8006/mcp")
MCP_WEB_CRAWLER_URL = os.getenv("MCP_WEB_CRAWLER_URL", "http://localhost:11235")
MCP_SUMMARIZER_URL = os.getenv("MCP_SUMMARIZER_URL", "http://localhost:8007/mcp")

# --- LLM ---

LLM_MODEL = os.getenv("LLM_MODEL", "openrouter:openai/gpt-4o-mini")


# --- Config Loaders ---


def load_sources_config() -> dict:
    """Load source priority configuration from config/sources.yml."""
    sources_path = AGENT_DIR / "config" / "sources.yml"
    with open(sources_path) as f:
        return yaml.safe_load(f)


def get_source_domains_by_tier() -> dict[str, list[str]]:
    """Return a dict mapping tier name to list of domains."""
    config = load_sources_config()
    tiers = config.get("source_tiers", {})
    return {
        tier_name: tier_data.get("domains", [])
        for tier_name, tier_data in tiers.items()
    }


def get_all_trusted_domains() -> list[str]:
    """Return a flat list of all trusted domains across all tiers."""
    domains = []
    for tier_domains in get_source_domains_by_tier().values():
        domains.extend(tier_domains)
    return domains


def get_source_tier_for_domain(domain: str) -> str | None:
    """Return the tier name for a domain, or None if not recognized."""
    for tier_name, tier_domains in get_source_domains_by_tier().items():
        for tier_domain in tier_domains:
            if tier_domain in domain or domain in tier_domain:
                return tier_name
    return None


def get_source_weight(tier_name: str) -> float:
    """Return the confidence weight for a source tier."""
    config = load_sources_config()
    tiers = config.get("source_tiers", {})
    tier = tiers.get(tier_name, {})
    return tier.get("weight", 0.0)


def load_research_topics() -> dict:
    """Load research topic configuration from config/research_topics.yml.

    Returns the full YAML structure. Callers access topics via
    result["topics"][topic_key].
    """
    topics_path = AGENT_DIR / "config" / "research_topics.yml"
    with open(topics_path) as f:
        return yaml.safe_load(f)


# --- Topic Accessors ---

_TOPICS_CONFIG = load_research_topics()["topics"]


def get_topic_instructions(topic_key: str) -> str:
    """Return the research instructions template for a topic."""
    return _TOPICS_CONFIG[topic_key]["instructions"]


def get_topic_section_header(topic_key: str) -> str:
    """Return the section header for a topic."""
    return _TOPICS_CONFIG[topic_key]["section_header"]


def get_topic_schema_hints(topic_key: str) -> str:
    """Return the schema hints for a topic."""
    return _TOPICS_CONFIG[topic_key]["schema_hints"]
