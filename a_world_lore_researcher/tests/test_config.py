"""Tests for configuration module — env var loading, source priority, and research topics."""

import pytest

from src.config import (
    AGENT_ID,
    AGENT_ROLE,
    CRAWL_CONTENT_TRUNCATE_CHARS,
    DAILY_TOKEN_BUDGET,
    EXTRACT_CONTENT_CHAR_LIMIT,
    GAME_NAME,
    JOB_QUEUE,
    MAX_RESEARCH_VALIDATE_ITERATIONS,
    MCP_STORAGE_URL,
    MCP_SUMMARIZER_URL,
    MCP_WEB_CRAWLER_URL,
    MCP_WEB_SEARCH_URL,
    PER_ZONE_TOKEN_BUDGET,
    RABBITMQ_URL,
    RATE_LIMIT_REQUESTS_PER_MINUTE,
    STATUS_QUEUE,
    VALIDATOR_QUEUE,
    _TOPICS_CONFIG,
    get_all_trusted_domains,
    get_source_domains_by_tier,
    get_source_tier_for_domain,
    get_source_weight,
    get_topic_instructions,
    get_topic_schema_hints,
    get_topic_section_header,
    load_research_topics,
    load_sources_config,
)


class TestEnvVarDefaults:
    def test_agent_identity(self):
        assert AGENT_ID == "world_lore_researcher"
        assert AGENT_ROLE == "world_lore_researcher"

    def test_game_config(self):
        assert GAME_NAME == "wow"

    def test_budget_defaults(self):
        assert DAILY_TOKEN_BUDGET == 500_000
        assert PER_ZONE_TOKEN_BUDGET == 50_000

    def test_rate_limiting(self):
        assert RATE_LIMIT_REQUESTS_PER_MINUTE == 30

    def test_validation(self):
        assert MAX_RESEARCH_VALIDATE_ITERATIONS == 3

    def test_service_urls(self):
        assert "5672" in RABBITMQ_URL
        assert "8005" in MCP_STORAGE_URL
        assert "8006" in MCP_WEB_SEARCH_URL
        assert "11235" in MCP_WEB_CRAWLER_URL
        assert MCP_WEB_CRAWLER_URL.endswith("11235")

    def test_queue_defaults(self):
        assert JOB_QUEUE == "agent.world_lore_researcher.jobs"
        assert STATUS_QUEUE == "agent.world_lore_researcher.status"

    def test_summarizer_url(self):
        assert "8007" in MCP_SUMMARIZER_URL

    def test_centralized_constants(self):
        assert EXTRACT_CONTENT_CHAR_LIMIT == 300_000
        assert CRAWL_CONTENT_TRUNCATE_CHARS == 5_000
        assert VALIDATOR_QUEUE == "agent.world_lore_validator"


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


class TestResearchTopics:
    def test_load_research_topics_returns_dict(self):
        config = load_research_topics()
        assert isinstance(config, dict)
        assert "topics" in config

    def test_all_five_topics_present(self):
        topics = load_research_topics()["topics"]
        expected = {
            "zone_overview_research",
            "npc_research",
            "faction_research",
            "lore_research",
            "narrative_items_research",
        }
        assert set(topics.keys()) == expected

    def test_each_topic_has_required_fields(self):
        topics = load_research_topics()["topics"]
        for key, topic in topics.items():
            assert "section_header" in topic, f"{key} missing section_header"
            assert "schema_hints" in topic, f"{key} missing schema_hints"
            assert "instructions" in topic, f"{key} missing instructions"

    def test_instructions_have_placeholders(self):
        topics = load_research_topics()["topics"]
        for key, topic in topics.items():
            assert "{zone}" in topic["instructions"], f"{key} missing {{zone}} placeholder"
            assert "{game}" in topic["instructions"], f"{key} missing {{game}} placeholder"

    def test_section_headers_are_markdown(self):
        topics = load_research_topics()["topics"]
        for key, topic in topics.items():
            assert topic["section_header"].startswith("## "), f"{key} header not markdown h2"

    def test_schema_hints_contain_must_preserve(self):
        topics = load_research_topics()["topics"]
        for key, topic in topics.items():
            if key != "narrative_items_research":
                assert "MUST PRESERVE" in topic["schema_hints"], f"{key} missing MUST PRESERVE"

    def test_instructions_format_with_zone_and_game(self):
        topics = load_research_topics()["topics"]
        for key, topic in topics.items():
            formatted = topic["instructions"].format(zone="Westfall", game="wow")
            assert "Westfall" in formatted
            assert "wow" in formatted


class TestTopicAccessors:
    """Tests for the topic accessor functions moved from pipeline.py."""

    def test_topics_config_has_five_entries(self):
        assert len(_TOPICS_CONFIG) == 5

    def test_get_topic_instructions_returns_string(self):
        result = get_topic_instructions("zone_overview_research")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_topic_instructions_all_topics(self):
        expected_topics = [
            "zone_overview_research",
            "npc_research",
            "faction_research",
            "lore_research",
            "narrative_items_research",
        ]
        for topic in expected_topics:
            result = get_topic_instructions(topic)
            assert "{zone}" in result, f"{topic} missing {{zone}} placeholder"
            assert "{game}" in result, f"{topic} missing {{game}} placeholder"

    def test_get_topic_instructions_format(self):
        result = get_topic_instructions("zone_overview_research")
        formatted = result.format(zone="Elwynn Forest", game="wow")
        assert "Elwynn Forest" in formatted
        assert "wow" in formatted

    def test_get_topic_instructions_invalid_key(self):
        with pytest.raises(KeyError):
            get_topic_instructions("nonexistent_topic")

    def test_get_topic_section_header_returns_markdown(self):
        result = get_topic_section_header("zone_overview_research")
        assert result.startswith("## ")

    def test_get_topic_section_header_all_topics(self):
        for topic in _TOPICS_CONFIG:
            result = get_topic_section_header(topic)
            assert isinstance(result, str)
            assert result.startswith("## ")

    def test_get_topic_section_header_invalid_key(self):
        with pytest.raises(KeyError):
            get_topic_section_header("nonexistent_topic")

    def test_get_topic_schema_hints_returns_string(self):
        result = get_topic_schema_hints("npc_research")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_topic_schema_hints_npc_content(self):
        result = get_topic_schema_hints("npc_research")
        assert "personality" in result.lower()

    def test_get_topic_schema_hints_all_topics(self):
        for topic in _TOPICS_CONFIG:
            result = get_topic_schema_hints(topic)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_get_topic_schema_hints_invalid_key(self):
        with pytest.raises(KeyError):
            get_topic_schema_hints("nonexistent_topic")
