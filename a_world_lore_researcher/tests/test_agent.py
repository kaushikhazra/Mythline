"""Tests for the LLM-powered research agent — extraction, cross-reference, research, discovery."""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

import src.agent as agent_module
from src.agent import (
    EXTRACTION_CATEGORIES,
    ZoneExtraction,
    CrossReferenceResult,
    ResearchResult,
    ResearchContext,
    ConnectedZonesResult,
    NPCExtractionResult,
    FactionExtractionResult,
    LoreExtractionResult,
    NarrativeItemExtractionResult,
    _make_source_ref,
    _normalize_url,
)
from shared.prompt_loader import load_prompt
from src.models import (
    ZoneData,
    NPCData,
    FactionData,
    LoreData,
    NarrativeItemData,
    SourceReference,
    SourceTier,
    Conflict,
)


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-for-tests")
    monkeypatch.setenv("MCP_WEB_SEARCH_URL", "http://localhost:8006/mcp")
    monkeypatch.setenv("MCP_WEB_CRAWLER_URL", "http://localhost:11235")


def _make_researcher():
    from src.agent import LoreResearcher
    return LoreResearcher()


# --- Prompt loading ---


class TestLoadPrompt:
    def test_loads_system_prompt(self):
        prompt = load_prompt(agent_module.__file__, "system_prompt")
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_loads_cross_reference_prompt(self):
        prompt = load_prompt(agent_module.__file__, "cross_reference")
        assert isinstance(prompt, str)
        assert "completeness" in prompt.lower()
        assert "confidence" in prompt.lower()
        assert "cross-category" in prompt.lower()

    def test_loads_cross_reference_task_prompt(self):
        prompt = load_prompt(agent_module.__file__, "cross_reference_task")
        assert isinstance(prompt, str)
        assert "{zone_name}" in prompt
        assert "{full_data}" in prompt
        assert "zone" in prompt and "npcs" in prompt and "factions" in prompt

    def test_loads_discover_zones_prompt(self):
        prompt = load_prompt(agent_module.__file__, "discover_zones")
        assert isinstance(prompt, str)
        assert "connected" in prompt.lower() or "adjacent" in prompt.lower()

    def test_loads_research_zone_prompt_with_two_phase(self):
        prompt = load_prompt(agent_module.__file__, "research_zone")
        assert isinstance(prompt, str)
        assert "{zone_name}" in prompt
        assert "Phase 1" in prompt
        assert "Phase 2" in prompt
        assert "{instructions}" in prompt

    def test_loads_extract_zone_prompt(self):
        prompt = load_prompt(agent_module.__file__, "extract_zone")
        assert isinstance(prompt, str)
        assert "{zone_name}" in prompt
        assert "{source_info}" in prompt
        assert "{raw_content}" in prompt
        assert "narrative_arc" in prompt

    def test_loads_extract_npcs_prompt(self):
        prompt = load_prompt(agent_module.__file__, "extract_npcs")
        assert isinstance(prompt, str)
        assert "{zone_name}" in prompt
        assert "{source_info}" in prompt
        assert "{raw_content}" in prompt
        assert "personality" in prompt.lower()
        assert "hostile" in prompt.lower()

    def test_loads_extract_factions_prompt(self):
        prompt = load_prompt(agent_module.__file__, "extract_factions")
        assert isinstance(prompt, str)
        assert "{zone_name}" in prompt
        assert "{source_info}" in prompt
        assert "{raw_content}" in prompt
        assert "ideology" in prompt.lower()

    def test_loads_extract_lore_prompt(self):
        prompt = load_prompt(agent_module.__file__, "extract_lore")
        assert isinstance(prompt, str)
        assert "{zone_name}" in prompt
        assert "{source_info}" in prompt
        assert "{raw_content}" in prompt
        assert "history, mythology, cosmology, power_source" in prompt

    def test_loads_extract_narrative_items_prompt(self):
        prompt = load_prompt(agent_module.__file__, "extract_narrative_items")
        assert isinstance(prompt, str)
        assert "{zone_name}" in prompt
        assert "{source_info}" in prompt
        assert "{raw_content}" in prompt
        assert "significance" in prompt.lower()

    def test_extract_zone_data_prompt_removed(self):
        """Old combined extraction prompt should be deleted."""
        with pytest.raises(FileNotFoundError):
            load_prompt(agent_module.__file__, "extract_zone_data")


# --- Output models ---


class TestZoneExtraction:
    def test_minimal_extraction(self):
        extraction = ZoneExtraction(
            zone=ZoneData(name="Elwynn Forest"),
        )
        assert extraction.zone.name == "Elwynn Forest"
        assert extraction.npcs == []
        assert extraction.factions == []

    def test_full_extraction(self):
        extraction = ZoneExtraction(
            zone=ZoneData(name="Elwynn Forest", narrative_arc="Peaceful beginnings"),
            npcs=[NPCData(name="Marshal Dughan")],
            factions=[FactionData(name="Stormwind Guard")],
            lore=[LoreData(title="History of Elwynn")],
            narrative_items=[NarrativeItemData(name="Hogger's Claw")],
        )
        assert len(extraction.npcs) == 1
        assert len(extraction.factions) == 1
        assert len(extraction.lore) == 1
        assert len(extraction.narrative_items) == 1

    def test_serialization_roundtrip(self):
        extraction = ZoneExtraction(
            zone=ZoneData(name="Westfall"),
            npcs=[NPCData(name="Gryan Stoutmantle")],
        )
        json_str = extraction.model_dump_json()
        restored = ZoneExtraction.model_validate_json(json_str)
        assert restored.zone.name == "Westfall"
        assert restored.npcs[0].name == "Gryan Stoutmantle"


class TestExtractionResultModels:
    """Tests for per-category extraction result wrapper models."""

    def test_npc_extraction_result_defaults(self):
        result = NPCExtractionResult()
        assert result.npcs == []

    def test_npc_extraction_result_populated(self):
        result = NPCExtractionResult(npcs=[NPCData(name="Edwin VanCleef")])
        assert len(result.npcs) == 1
        assert result.npcs[0].name == "Edwin VanCleef"

    def test_faction_extraction_result_defaults(self):
        result = FactionExtractionResult()
        assert result.factions == []

    def test_faction_extraction_result_populated(self):
        result = FactionExtractionResult(factions=[FactionData(name="Defias Brotherhood")])
        assert len(result.factions) == 1

    def test_lore_extraction_result_defaults(self):
        result = LoreExtractionResult()
        assert result.lore == []

    def test_lore_extraction_result_populated(self):
        result = LoreExtractionResult(lore=[LoreData(title="Stonemasons' Betrayal")])
        assert len(result.lore) == 1

    def test_narrative_item_extraction_result_defaults(self):
        result = NarrativeItemExtractionResult()
        assert result.narrative_items == []

    def test_narrative_item_extraction_result_populated(self):
        result = NarrativeItemExtractionResult(
            narrative_items=[NarrativeItemData(name="VanCleef's Sword")]
        )
        assert len(result.narrative_items) == 1

    def test_serialization_roundtrip(self):
        result = NPCExtractionResult(npcs=[NPCData(name="Test NPC", personality="Brave")])
        json_str = result.model_dump_json()
        restored = NPCExtractionResult.model_validate_json(json_str)
        assert restored.npcs[0].name == "Test NPC"
        assert restored.npcs[0].personality == "Brave"


class TestExtractionCategories:
    """Tests for the EXTRACTION_CATEGORIES config dict."""

    def test_has_five_categories(self):
        assert len(EXTRACTION_CATEGORIES) == 5

    def test_expected_keys(self):
        expected = {"zone", "npcs", "factions", "lore", "narrative_items"}
        assert set(EXTRACTION_CATEGORIES.keys()) == expected

    def test_token_shares_sum_to_one(self):
        total = sum(share for _, _, share in EXTRACTION_CATEGORIES.values())
        assert abs(total - 1.0) < 0.001

    def test_each_entry_has_correct_structure(self):
        from pydantic import BaseModel
        for key, (output_type, prompt_name, share) in EXTRACTION_CATEGORIES.items():
            assert issubclass(output_type, BaseModel), f"{key} output_type not BaseModel"
            assert isinstance(prompt_name, str), f"{key} prompt_name not str"
            assert 0 < share <= 1.0, f"{key} share out of range"

    def test_prompt_names_match_files(self):
        """Each prompt_name in EXTRACTION_CATEGORIES must load successfully."""
        for key, (_, prompt_name, _) in EXTRACTION_CATEGORIES.items():
            prompt = load_prompt(agent_module.__file__, prompt_name)
            assert isinstance(prompt, str) and len(prompt) > 0, f"Prompt {prompt_name} failed"


class TestCrossReferenceResult:
    def test_consistent_result(self):
        result = CrossReferenceResult(
            is_consistent=True,
            confidence={"zone": 0.9, "npcs": 0.85},
        )
        assert result.is_consistent is True
        assert result.confidence["zone"] == 0.9

    def test_inconsistent_result(self):
        result = CrossReferenceResult(
            is_consistent=False,
            conflicts=[
                Conflict(
                    data_point="NPC faction",
                    source_a=SourceReference(url="https://a.com", domain="a.com", tier=SourceTier.PRIMARY),
                    claim_a="Alliance",
                    source_b=SourceReference(url="https://b.com", domain="b.com", tier=SourceTier.TERTIARY),
                    claim_b="Neutral",
                )
            ],
        )
        assert result.is_consistent is False
        assert len(result.conflicts) == 1


class TestResearchResult:
    def test_empty_result(self):
        result = ResearchResult()
        assert result.raw_content == []
        assert result.sources == []
        assert result.summary == ""

    def test_populated_result(self):
        result = ResearchResult(
            raw_content=["# Zone content"],
            sources=[SourceReference(url="https://x.com", domain="x.com", tier=SourceTier.PRIMARY)],
            summary="Found zone data.",
        )
        assert len(result.raw_content) == 1
        assert len(result.sources) == 1


class TestConnectedZonesResult:
    def test_zone_slugs(self):
        result = ConnectedZonesResult(zone_slugs=["westfall", "stormwind_city"])
        assert len(result.zone_slugs) == 2


# --- ResearchContext ---


class TestResearchContext:
    def test_defaults_empty(self):
        ctx = ResearchContext()
        assert ctx.raw_content == []
        assert ctx.sources == []

    def test_accumulates(self):
        ctx = ResearchContext()
        ctx.raw_content.append("content 1")
        ctx.sources.append(SourceReference(url="https://x.com", domain="x.com", tier=SourceTier.PRIMARY))
        assert len(ctx.raw_content) == 1
        assert len(ctx.sources) == 1


# --- Helper ---


class TestMakeSourceRef:
    def test_known_domain(self):
        ref = _make_source_ref("https://wowpedia.fandom.com/wiki/Elwynn")
        assert ref.domain == "wowpedia.fandom.com"

    def test_unknown_domain_defaults_tertiary(self):
        ref = _make_source_ref("https://random-blog.com/wow-guide")
        assert ref.domain == "random-blog.com"
        assert ref.tier == SourceTier.TERTIARY


class TestNormalizeUrl:
    def test_strips_trailing_slash(self):
        assert _normalize_url("https://wiki.gg/page/") == "https://wiki.gg/page"

    def test_strips_fragment(self):
        assert _normalize_url("https://wiki.gg/page#section") == "https://wiki.gg/page"

    def test_strips_both(self):
        assert _normalize_url("https://wiki.gg/page/#section") == "https://wiki.gg/page"

    def test_no_change_needed(self):
        assert _normalize_url("https://wiki.gg/page") == "https://wiki.gg/page"

    def test_preserves_query_params(self):
        assert _normalize_url("https://wiki.gg/page?id=1") == "https://wiki.gg/page?id=1"

    def test_empty_fragment(self):
        assert _normalize_url("https://wiki.gg/page#") == "https://wiki.gg/page"


# --- LoreResearcher init ---


class TestLoreResearcherInit:
    def test_creates_per_category_extraction_agents(self):
        researcher = _make_researcher()
        assert isinstance(researcher._extraction_agents, dict)
        assert len(researcher._extraction_agents) == 5
        for key in EXTRACTION_CATEGORIES:
            assert key in researcher._extraction_agents

    def test_creates_core_agents(self):
        researcher = _make_researcher()
        assert researcher._cross_ref_agent is not None
        assert researcher._research_agent is not None
        assert researcher._zone_discovery_agent is not None

    def test_has_crawl_cache(self):
        researcher = _make_researcher()
        assert isinstance(researcher._crawl_cache, dict)
        assert len(researcher._crawl_cache) == 0


class TestResetZoneState:
    def test_clears_tokens_and_cache(self):
        researcher = _make_researcher()
        researcher._zone_tokens = 1000
        researcher._crawl_cache["https://wiki.gg/page"] = "content"

        researcher.reset_zone_state()

        assert researcher._zone_tokens == 0
        assert len(researcher._crawl_cache) == 0


# --- extract_category ---


class TestExtractCategory:
    @pytest.mark.asyncio
    async def test_extract_category_calls_correct_agent(self):
        researcher = _make_researcher()

        mock_zone_data = ZoneData(name="Elwynn Forest", narrative_arc="Starting zone")
        mock_result = MagicMock()
        mock_result.output = mock_zone_data

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)
        researcher._extraction_agents["zone"] = mock_agent

        sources = [
            SourceReference(url="https://wowpedia.fandom.com/wiki/Elwynn", domain="wowpedia.fandom.com", tier=SourceTier.OFFICIAL),
        ]

        result = await researcher.extract_category(
            "zone", "elwynn_forest", "# Zone content", sources,
        )

        assert result.name == "Elwynn Forest"
        mock_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_category_npcs(self):
        researcher = _make_researcher()

        mock_npcs = NPCExtractionResult(npcs=[NPCData(name="Marshal Dughan")])
        mock_result = MagicMock()
        mock_result.output = mock_npcs

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)
        researcher._extraction_agents["npcs"] = mock_agent

        sources = [
            SourceReference(url="https://wiki.gg/npc", domain="wiki.gg", tier=SourceTier.PRIMARY),
        ]

        result = await researcher.extract_category(
            "npcs", "elwynn_forest", "# NPC content", sources,
        )

        assert len(result.npcs) == 1
        assert result.npcs[0].name == "Marshal Dughan"

    @pytest.mark.asyncio
    async def test_extract_category_uses_correct_token_budget(self):
        researcher = _make_researcher()

        mock_result = MagicMock()
        mock_result.output = ZoneData(name="Test")

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)
        researcher._extraction_agents["zone"] = mock_agent

        await researcher.extract_category("zone", "test", "", [])

        # Verify usage_limits were passed with correct budget share (10%)
        call_kwargs = mock_agent.run.call_args[1]
        budget = call_kwargs["usage_limits"].output_tokens_limit
        from src.config import PER_ZONE_TOKEN_BUDGET
        assert budget == int(PER_ZONE_TOKEN_BUDGET * 0.10)


# --- cross_reference ---


class TestCrossReference:
    @pytest.mark.asyncio
    async def test_cross_reference_calls_agent(self):
        researcher = _make_researcher()

        mock_cr_result = CrossReferenceResult(
            is_consistent=True,
            confidence={"zone": 0.95, "npcs": 0.9},
        )

        mock_result = MagicMock()
        mock_result.output = mock_cr_result

        researcher._cross_ref_agent = MagicMock()
        researcher._cross_ref_agent.run = AsyncMock(return_value=mock_result)

        extraction = ZoneExtraction(
            zone=ZoneData(name="Elwynn Forest"),
            npcs=[NPCData(name="Marshal Dughan")],
        )

        result = await researcher.cross_reference(extraction)

        assert result.is_consistent is True
        assert result.confidence["zone"] == 0.95
        researcher._cross_ref_agent.run.assert_called_once()


# --- research_zone ---


class TestResearchZone:
    @pytest.mark.asyncio
    async def test_returns_research_result(self):
        researcher = _make_researcher()

        mock_result = MagicMock()
        mock_result.output = "Researched Elwynn Forest successfully."

        researcher._research_agent = MagicMock()
        researcher._research_agent.run = AsyncMock(return_value=mock_result)
        # Mock MCP server context managers
        researcher._mcp_servers = []

        result = await researcher.research_zone("elwynn_forest")

        assert isinstance(result, ResearchResult)
        assert result.summary == "Researched Elwynn Forest successfully."
        researcher._research_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_captures_deps_content(self):
        """Verify that content appended to deps during agent run appears in result."""
        researcher = _make_researcher()

        # Simulate agent run that populates deps via tool calls
        async def mock_run(prompt, deps=None, usage_limits=None):
            # Simulate what the crawl tool would do during a real run
            if deps is not None:
                deps.raw_content.append("Crawled page content")
                deps.sources.append(SourceReference(
                    url="https://wowpedia.fandom.com/wiki/Elwynn",
                    domain="wowpedia.fandom.com",
                    tier=SourceTier.OFFICIAL,
                ))
            result = MagicMock()
            result.output = "Summary of research"
            return result

        researcher._research_agent = MagicMock()
        researcher._research_agent.run = AsyncMock(side_effect=mock_run)
        researcher._mcp_servers = []

        result = await researcher.research_zone("elwynn_forest")

        assert len(result.raw_content) == 1
        assert result.raw_content[0] == "Crawled page content"
        assert len(result.sources) == 1
        assert result.sources[0].domain == "wowpedia.fandom.com"


# --- discover_connected_zones ---


class TestDiscoverConnectedZones:
    @pytest.mark.asyncio
    async def test_returns_zone_slugs(self):
        researcher = _make_researcher()

        mock_result = MagicMock()
        mock_result.output = ConnectedZonesResult(
            zone_slugs=["westfall", "stormwind_city"]
        )

        researcher._zone_discovery_agent = MagicMock()
        researcher._zone_discovery_agent.run = AsyncMock(return_value=mock_result)
        researcher._mcp_servers = []

        result = await researcher.discover_connected_zones("elwynn_forest")

        assert result == ["westfall", "stormwind_city"]
        researcher._zone_discovery_agent.run.assert_called_once()
