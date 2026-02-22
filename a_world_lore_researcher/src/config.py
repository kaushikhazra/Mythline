"""Configuration loader for the World Lore Researcher agent."""

from __future__ import annotations

import os
from pathlib import Path

import yaml


AGENT_DIR = Path(__file__).parent.parent


def _int_env(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


AGENT_ID = os.getenv("AGENT_ID", "world_lore_researcher")
AGENT_ROLE = os.getenv("AGENT_ROLE", "world_lore_researcher")
GAME_NAME = os.getenv("GAME_NAME", "wow")
STARTING_ZONE = os.getenv("STARTING_ZONE", "elwynn_forest")

RESEARCH_CYCLE_DELAY_MINUTES = _int_env("RESEARCH_CYCLE_DELAY_MINUTES", 5)
DAILY_TOKEN_BUDGET = _int_env("DAILY_TOKEN_BUDGET", 500_000)
PER_CYCLE_TOKEN_BUDGET = _int_env("PER_CYCLE_TOKEN_BUDGET", 50_000)
MAX_RESEARCH_VALIDATE_ITERATIONS = _int_env("MAX_RESEARCH_VALIDATE_ITERATIONS", 3)
RATE_LIMIT_REQUESTS_PER_MINUTE = _int_env("RATE_LIMIT_REQUESTS_PER_MINUTE", 30)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://mythline:mythline@localhost:5672/")
MCP_STORAGE_URL = os.getenv("MCP_STORAGE_URL", "http://localhost:8005/mcp")
MCP_WEB_SEARCH_URL = os.getenv("MCP_WEB_SEARCH_URL", "http://localhost:8006/mcp")
MCP_WEB_CRAWLER_URL = os.getenv("MCP_WEB_CRAWLER_URL", "http://localhost:11235")

LLM_MODEL = os.getenv("LLM_MODEL", "openrouter:openai/gpt-4o-mini")


def load_sources_config() -> dict:
    sources_path = AGENT_DIR / "config" / "sources.yml"
    with open(sources_path) as f:
        return yaml.safe_load(f)


def get_source_domains_by_tier() -> dict[str, list[str]]:
    config = load_sources_config()
    tiers = config.get("source_tiers", {})
    return {
        tier_name: tier_data.get("domains", [])
        for tier_name, tier_data in tiers.items()
    }


def get_all_trusted_domains() -> list[str]:
    domains = []
    for tier_domains in get_source_domains_by_tier().values():
        domains.extend(tier_domains)
    return domains


def get_source_tier_for_domain(domain: str) -> str | None:
    for tier_name, tier_domains in get_source_domains_by_tier().items():
        for tier_domain in tier_domains:
            if tier_domain in domain or domain in tier_domain:
                return tier_name
    return None


def get_source_weight(tier_name: str) -> float:
    config = load_sources_config()
    tiers = config.get("source_tiers", {})
    tier = tiers.get(tier_name, {})
    return tier.get("weight", 0.0)
