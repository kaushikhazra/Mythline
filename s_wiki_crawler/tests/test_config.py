"""Tests for configuration loading."""

import pytest

from src.config import (
    get_all_trusted_domains,
    get_domain_tier,
    load_crawl_scope,
    load_sources_config,
    reset_config_cache,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear config cache before each test."""
    reset_config_cache()
    yield
    reset_config_cache()


class TestLoadCrawlScope:
    def test_loads_successfully(self):
        scope = load_crawl_scope()
        assert len(scope.categories) > 0

    def test_has_expected_categories(self):
        scope = load_crawl_scope()
        expected = {"zone_overview", "npcs", "factions", "lore", "quests", "narrative_items"}
        assert expected == set(scope.categories.keys())

    def test_each_category_has_queries(self):
        scope = load_crawl_scope()
        for name, cat in scope.categories.items():
            assert len(cat.search_queries) > 0, f"{name} has no search queries"
            assert len(cat.preferred_domains) > 0, f"{name} has no preferred domains"

    def test_query_templates_have_placeholders(self):
        scope = load_crawl_scope()
        for name, cat in scope.categories.items():
            for query in cat.search_queries:
                assert "{zone}" in query, f"{name} query missing {{zone}}: {query}"

    def test_caching(self):
        scope1 = load_crawl_scope()
        scope2 = load_crawl_scope()
        assert scope1 is scope2


class TestLoadSourcesConfig:
    def test_loads_successfully(self):
        sources = load_sources_config()
        assert "source_tiers" in sources

    def test_has_expected_tiers(self):
        sources = load_sources_config()
        tiers = set(sources["source_tiers"].keys())
        assert "official" in tiers
        assert "primary" in tiers

    def test_each_tier_has_weight(self):
        sources = load_sources_config()
        for name, tier in sources["source_tiers"].items():
            assert "weight" in tier, f"{name} tier missing weight"
            assert 0 < tier["weight"] <= 1.0

    def test_caching(self):
        s1 = load_sources_config()
        s2 = load_sources_config()
        assert s1 is s2


class TestGetDomainTier:
    def test_official_domain(self):
        tier, weight = get_domain_tier("wowpedia.fandom.com")
        assert tier == "official"
        assert weight == 1.0

    def test_primary_domain(self):
        tier, weight = get_domain_tier("warcraft.wiki.gg")
        assert tier == "primary"
        assert weight == 0.8

    def test_unknown_domain(self):
        tier, weight = get_domain_tier("randomsite.com")
        assert tier == "unknown"
        assert weight == 0.3

    def test_secondary_domain(self):
        tier, weight = get_domain_tier("icy-veins.com")
        assert tier == "secondary"
        assert weight == 0.6


class TestGetAllTrustedDomains:
    def test_returns_domains(self):
        domains = get_all_trusted_domains()
        assert len(domains) > 0
        assert "wowpedia.fandom.com" in domains
        assert "warcraft.wiki.gg" in domains
