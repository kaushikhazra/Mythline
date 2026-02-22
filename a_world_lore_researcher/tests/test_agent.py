"""Tests for the LLM-powered research agent — extraction, cross-reference, research, discovery."""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

import src.agent as agent_module
from src.agent import (
    ZoneExtraction,
    CrossReferenceResult,
    ResearchResult,
    ResearchContext,
    ConnectedZonesResult,
    _make_source_ref,
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
        assert "consistency" in prompt.lower()
        assert "confidence" in prompt.lower()

    def test_loads_discover_zones_prompt(self):
        prompt = load_prompt(agent_module.__file__, "discover_zones")
        assert isinstance(prompt, str)
        assert "connected" in prompt.lower() or "adjacent" in prompt.lower()

    def test_loads_research_zone_prompt(self):
        prompt = load_prompt(agent_module.__file__, "research_zone")
        assert isinstance(prompt, str)
        assert "{zone_name}" in prompt


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


# --- LoreResearcher init ---


class TestLoreResearcherInit:
    def test_creates_agents(self):
        researcher = _make_researcher()
        assert researcher._extraction_agent is not None
        assert researcher._cross_ref_agent is not None
        assert researcher._research_agent is not None
        assert researcher._zone_discovery_agent is not None


# --- extract_zone_data ---


class TestExtractZoneData:
    @pytest.mark.asyncio
    async def test_extract_zone_data_calls_agent(self):
        researcher = _make_researcher()

        mock_extraction = ZoneExtraction(
            zone=ZoneData(name="Elwynn Forest", narrative_arc="Starting zone"),
            npcs=[NPCData(name="Marshal Dughan")],
        )

        mock_result = MagicMock()
        mock_result.output = mock_extraction

        researcher._extraction_agent = MagicMock()
        researcher._extraction_agent.run = AsyncMock(return_value=mock_result)

        sources = [
            SourceReference(url="https://wowpedia.fandom.com/wiki/Elwynn", domain="wowpedia.fandom.com", tier=SourceTier.OFFICIAL),
        ]

        result = await researcher.extract_zone_data(
            zone_name="elwynn_forest",
            raw_content=["# Elwynn Forest\nA peaceful forest..."],
            sources=sources,
        )

        assert result.zone.name == "Elwynn Forest"
        assert len(result.npcs) == 1
        researcher._extraction_agent.run.assert_called_once()


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
