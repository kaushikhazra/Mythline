"""Tests for configuration module — env var loading and source priority."""

import os

from src.config import (
    AGENT_ID,
    AGENT_ROLE,
    DAILY_TOKEN_BUDGET,
    GAME_NAME,
    MAX_RESEARCH_VALIDATE_ITERATIONS,
    MCP_STORAGE_URL,
    MCP_WEB_CRAWLER_URL,
    MCP_WEB_SEARCH_URL,
    PER_CYCLE_TOKEN_BUDGET,
    RABBITMQ_URL,
    RATE_LIMIT_REQUESTS_PER_MINUTE,
    RESEARCH_CYCLE_DELAY_MINUTES,
    STARTING_ZONE,
    get_all_trusted_domains,
    get_source_domains_by_tier,
    get_source_tier_for_domain,
    get_source_weight,
    load_sources_config,
)


class TestEnvVarDefaults:
    def test_agent_identity(self):
        assert AGENT_ID == "world_lore_researcher"
        assert AGENT_ROLE == "world_lore_researcher"

    def test_game_config(self):
        assert GAME_NAME == "wow"
        assert STARTING_ZONE == "elwynn_forest"

    def test_budget_defaults(self):
        assert DAILY_TOKEN_BUDGET == 500_000
        assert PER_CYCLE_TOKEN_BUDGET == 50_000

    def test_rate_limiting(self):
        assert RATE_LIMIT_REQUESTS_PER_MINUTE == 30
        assert RESEARCH_CYCLE_DELAY_MINUTES == 5

    def test_validation(self):
        assert MAX_RESEARCH_VALIDATE_ITERATIONS == 3

    def test_service_urls(self):
        assert "5672" in RABBITMQ_URL
        assert "8005" in MCP_STORAGE_URL
        assert "8006" in MCP_WEB_SEARCH_URL
        assert "11235" in MCP_WEB_CRAWLER_URL
        assert MCP_WEB_CRAWLER_URL.endswith("11235")


class TestSourcesConfig:
    def test_load_sources_config(self):
        config = load_sources_config()
        assert config["game"] == "wow"
        assert "source_tiers" in config

    def test_get_source_domains_by_tier(self):
        tiers = get_source_domains_by_tier()
        assert "official" in tiers
        assert "primary" in tiers
        assert "secondary" in tiers
        assert "tertiary" in tiers
        assert "wowpedia.fandom.com" in tiers["official"]
        assert "warcraft.wiki.gg" in tiers["primary"]

    def test_get_all_trusted_domains(self):
        domains = get_all_trusted_domains()
        assert len(domains) > 0
        assert "wowpedia.fandom.com" in domains
        assert "warcraft.wiki.gg" in domains

    def test_get_source_tier_for_known_domain(self):
        assert get_source_tier_for_domain("wowpedia.fandom.com") == "official"
        assert get_source_tier_for_domain("warcraft.wiki.gg") == "primary"
        assert get_source_tier_for_domain("icy-veins.com") == "secondary"

    def test_get_source_tier_for_subdomain(self):
        assert get_source_tier_for_domain("www.warcraft.wiki.gg") == "primary"

    def test_get_source_tier_for_unknown_domain(self):
        assert get_source_tier_for_domain("randomsite.com") is None

    def test_get_source_weight(self):
        assert get_source_weight("official") == 1.0
        assert get_source_weight("primary") == 0.8
        assert get_source_weight("secondary") == 0.6
        assert get_source_weight("tertiary") == 0.4

    def test_get_source_weight_unknown_tier(self):
        assert get_source_weight("nonexistent") == 0.0
