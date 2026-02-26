"""Tests for the orchestrator tool functions — worker delegation and deps accumulation."""

from dataclasses import field
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from src.agent import EXTRACTION_CATEGORIES, OrchestratorContext, ResearchContext
from src.models import (
    ConnectedZonesResult,
    CrossReferenceResult,
    FactionData,
    FactionExtractionResult,
    LoreData,
    LoreExtractionResult,
    NPCData,
    NPCExtractionResult,
    NarrativeItemData,
    NarrativeItemExtractionResult,
    SourceReference,
    SourceTier,
    ZoneData,
)
from src.orchestrator_tools import (
    CATEGORY_TO_TOPIC,
    crawl_webpage,
    cross_reference,
    discover_zones,
    extract_category,
    research_topic,
    summarize_content,
)
from tests.factories import (
    make_cross_ref,
    make_faction,
    make_item,
    make_lore,
    make_npc,
    make_zone,
)

import src.agent as agent_module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_mock_result(output=None, total_tokens=100):
    """Create a mock agent run result with usage tracking."""
    result = MagicMock()
    result.output = output
    usage = MagicMock()
    usage.total_tokens = total_tokens
    result.usage.return_value = usage
    return result


def _make_context(**overrides) -> OrchestratorContext:
    """Create a minimal OrchestratorContext for testing."""
    defaults = dict(
        research_agent=MagicMock(),
        extraction_agents={
            cat: MagicMock() for cat in EXTRACTION_CATEGORIES
        },
        cross_ref_agent=MagicMock(),
        discovery_agent=MagicMock(),
        agent_file=agent_module.__file__,
        zone_name="elwynn_forest",
        game_name="wow",
        crawl_cache={},
    )
    defaults.update(overrides)
    return OrchestratorContext(**defaults)


def _make_run_context(deps: OrchestratorContext) -> MagicMock:
    """Create a mock RunContext wrapping the deps."""
    ctx = MagicMock()
    ctx.deps = deps
    return ctx


# ---------------------------------------------------------------------------
# CATEGORY_TO_TOPIC mapping
# ---------------------------------------------------------------------------


class TestCategoryToTopic:
    def test_has_five_entries(self):
        assert len(CATEGORY_TO_TOPIC) == 5

    def test_maps_correctly(self):
        assert CATEGORY_TO_TOPIC["zone"] == "zone_overview_research"
        assert CATEGORY_TO_TOPIC["npcs"] == "npc_research"
        assert CATEGORY_TO_TOPIC["factions"] == "faction_research"
        assert CATEGORY_TO_TOPIC["lore"] == "lore_research"
        assert CATEGORY_TO_TOPIC["narrative_items"] == "narrative_items_research"


# ---------------------------------------------------------------------------
# research_topic
# ---------------------------------------------------------------------------


class TestResearchTopic:
    @pytest.mark.asyncio
    async def test_delegates_to_research_agent(self):
        deps = _make_context()
        mock_result = _make_mock_result(output="Research done", total_tokens=500)

        async def mock_run(prompt, deps=None, usage_limits=None):
            if deps is not None:
                deps.raw_content.append("Crawled page about NPCs")
                deps.sources.append(SourceReference(
                    url="https://wowpedia.fandom.com/wiki/Elwynn",
                    domain="wowpedia.fandom.com",
                    tier=SourceTier.OFFICIAL,
                ))
            return mock_result

        deps.research_agent.run = AsyncMock(side_effect=mock_run)

        ctx = _make_run_context(deps)
        result = await research_topic(ctx, "npc_research")

        assert "npc_research" in result
        assert "1 content blocks" in result
        assert "1 sources" in result

    @pytest.mark.asyncio
    async def test_accumulates_in_deps(self):
        deps = _make_context()
        mock_result = _make_mock_result(total_tokens=300)

        async def mock_run(prompt, deps=None, usage_limits=None):
            if deps is not None:
                deps.raw_content.extend(["block1", "block2"])
                deps.sources.append(SourceReference(
                    url="https://wiki.gg/page",
                    domain="wiki.gg",
                    tier=SourceTier.PRIMARY,
                ))
            return mock_result

        deps.research_agent.run = AsyncMock(side_effect=mock_run)

        ctx = _make_run_context(deps)
        await research_topic(ctx, "zone_overview_research")

        assert "zone_overview_research" in deps.research_content
        assert len(deps.research_content["zone_overview_research"]) == 2
        assert len(deps.sources) == 1

    @pytest.mark.asyncio
    async def test_tracks_worker_tokens(self):
        deps = _make_context()
        mock_result = _make_mock_result(total_tokens=750)
        deps.research_agent.run = AsyncMock(return_value=mock_result)

        ctx = _make_run_context(deps)
        await research_topic(ctx, "lore_research")

        assert deps.worker_tokens == 750

    @pytest.mark.asyncio
    async def test_shares_crawl_cache(self):
        shared_cache = {"https://wiki.gg/cached": "cached content"}
        deps = _make_context(crawl_cache=shared_cache)
        mock_result = _make_mock_result(total_tokens=100)
        deps.research_agent.run = AsyncMock(return_value=mock_result)

        ctx = _make_run_context(deps)
        await research_topic(ctx, "zone_overview_research")

        # Verify the research agent received a context with the shared cache
        call_kwargs = deps.research_agent.run.call_args[1]
        research_ctx = call_kwargs["deps"]
        assert "https://wiki.gg/cached" in research_ctx.crawl_cache


# ---------------------------------------------------------------------------
# extract_category
# ---------------------------------------------------------------------------


class TestExtractCategory:
    @pytest.mark.asyncio
    async def test_extracts_zone_data(self):
        deps = _make_context()
        deps.research_content["zone_overview_research"] = ["Zone content here."]
        deps.sources = [SourceReference(
            url="https://wiki.gg/zone", domain="wiki.gg", tier=SourceTier.PRIMARY,
        )]

        mock_zone = make_zone(name="Elwynn Forest")
        mock_result = _make_mock_result(output=mock_zone, total_tokens=200)
        deps.extraction_agents["zone"].run = AsyncMock(return_value=mock_result)

        ctx = _make_run_context(deps)
        result = await extract_category(ctx, "zone")

        assert "Elwynn Forest" in result
        assert deps.zone_data is mock_zone

    @pytest.mark.asyncio
    async def test_extracts_npcs(self):
        deps = _make_context()
        deps.research_content["npc_research"] = ["NPC content."]

        mock_npcs = NPCExtractionResult(npcs=[
            make_npc(name="Marshal Dughan"),
            make_npc(name="Edwin VanCleef"),
        ])
        mock_result = _make_mock_result(output=mock_npcs, total_tokens=300)
        deps.extraction_agents["npcs"].run = AsyncMock(return_value=mock_result)

        ctx = _make_run_context(deps)
        result = await extract_category(ctx, "npcs")

        assert "2 NPCs" in result
        assert len(deps.npcs) == 2

    @pytest.mark.asyncio
    async def test_extracts_factions(self):
        deps = _make_context()
        deps.research_content["faction_research"] = ["Faction content."]

        mock_factions = FactionExtractionResult(factions=[make_faction(name="Defias")])
        mock_result = _make_mock_result(output=mock_factions, total_tokens=250)
        deps.extraction_agents["factions"].run = AsyncMock(return_value=mock_result)

        ctx = _make_run_context(deps)
        result = await extract_category(ctx, "factions")

        assert "1 factions" in result
        assert len(deps.factions) == 1

    @pytest.mark.asyncio
    async def test_extracts_lore(self):
        deps = _make_context()
        deps.research_content["lore_research"] = ["Lore content."]

        mock_lore = LoreExtractionResult(lore=[make_lore(title="History")])
        mock_result = _make_mock_result(output=mock_lore, total_tokens=250)
        deps.extraction_agents["lore"].run = AsyncMock(return_value=mock_result)

        ctx = _make_run_context(deps)
        result = await extract_category(ctx, "lore")

        assert "1 lore entries" in result
        assert len(deps.lore) == 1

    @pytest.mark.asyncio
    async def test_extracts_narrative_items(self):
        deps = _make_context()
        deps.research_content["narrative_items_research"] = ["Items content."]

        mock_items = NarrativeItemExtractionResult(
            narrative_items=[make_item(name="Hogger's Claw")]
        )
        mock_result = _make_mock_result(output=mock_items, total_tokens=150)
        deps.extraction_agents["narrative_items"].run = AsyncMock(return_value=mock_result)

        ctx = _make_run_context(deps)
        result = await extract_category(ctx, "narrative_items")

        assert "1 narrative items" in result
        assert len(deps.narrative_items) == 1

    @pytest.mark.asyncio
    async def test_no_content_returns_error(self):
        deps = _make_context()
        # No research content for the zone topic

        ctx = _make_run_context(deps)
        result = await extract_category(ctx, "zone")

        assert "No research content" in result
        assert deps.zone_data is None

    @pytest.mark.asyncio
    async def test_tracks_worker_tokens(self):
        deps = _make_context()
        deps.research_content["npc_research"] = ["content"]

        mock_result = _make_mock_result(
            output=NPCExtractionResult(npcs=[make_npc()]), total_tokens=400,
        )
        deps.extraction_agents["npcs"].run = AsyncMock(return_value=mock_result)

        ctx = _make_run_context(deps)
        await extract_category(ctx, "npcs")

        assert deps.worker_tokens == 400

    def test_empty_npcs_list_rejected(self):
        with pytest.raises(ValidationError, match="npcs"):
            NPCExtractionResult(npcs=[])

    def test_empty_factions_list_rejected(self):
        with pytest.raises(ValidationError, match="factions"):
            FactionExtractionResult(factions=[])

    def test_empty_lore_list_rejected(self):
        with pytest.raises(ValidationError, match="lore"):
            LoreExtractionResult(lore=[])

    def test_empty_narrative_items_list_rejected(self):
        with pytest.raises(ValidationError, match="narrative_items"):
            NarrativeItemExtractionResult(narrative_items=[])


# ---------------------------------------------------------------------------
# cross_reference
# ---------------------------------------------------------------------------


class TestCrossReference:
    @pytest.mark.asyncio
    async def test_cross_references_extracted_data(self):
        deps = _make_context()
        deps.zone_data = make_zone(name="Elwynn Forest")
        deps.npcs = [make_npc(name="Marshal Dughan")]

        mock_cr = make_cross_ref(confidence={"zone": 0.9, "npcs": 0.85})
        mock_result = _make_mock_result(output=mock_cr, total_tokens=600)
        deps.cross_ref_agent.run = AsyncMock(return_value=mock_result)

        ctx = _make_run_context(deps)
        result = await cross_reference(ctx)

        assert "consistent=True" in result
        assert deps.cross_ref_result is mock_cr

    @pytest.mark.asyncio
    async def test_no_zone_data_returns_error(self):
        deps = _make_context()
        # zone_data is None

        ctx = _make_run_context(deps)
        result = await cross_reference(ctx)

        assert "Error" in result
        assert "no zone data" in result

    @pytest.mark.asyncio
    async def test_tracks_worker_tokens(self):
        deps = _make_context()
        deps.zone_data = make_zone(name="Test")

        mock_cr = make_cross_ref(confidence={})
        mock_result = _make_mock_result(output=mock_cr, total_tokens=500)
        deps.cross_ref_agent.run = AsyncMock(return_value=mock_result)

        ctx = _make_run_context(deps)
        await cross_reference(ctx)

        assert deps.worker_tokens == 500


# ---------------------------------------------------------------------------
# discover_zones
# ---------------------------------------------------------------------------


class TestDiscoverZones:
    @pytest.mark.asyncio
    async def test_discovers_connected_zones(self):
        deps = _make_context()

        mock_zones = ConnectedZonesResult(
            zone_slugs=["westfall", "stormwind_city", "redridge_mountains"]
        )
        mock_result = _make_mock_result(output=mock_zones, total_tokens=200)
        deps.discovery_agent.run = AsyncMock(return_value=mock_result)

        ctx = _make_run_context(deps)
        result = await discover_zones(ctx)

        assert "3 connected zones" in result
        assert "westfall" in result
        assert deps.discovered_zones == ["westfall", "stormwind_city", "redridge_mountains"]

    @pytest.mark.asyncio
    async def test_truncates_preview_at_5(self):
        deps = _make_context()

        slugs = [f"zone_{i}" for i in range(8)]
        mock_zones = ConnectedZonesResult(zone_slugs=slugs)
        mock_result = _make_mock_result(output=mock_zones, total_tokens=200)
        deps.discovery_agent.run = AsyncMock(return_value=mock_result)

        ctx = _make_run_context(deps)
        result = await discover_zones(ctx)

        assert "8 connected zones" in result
        assert "..." in result

    @pytest.mark.asyncio
    async def test_tracks_worker_tokens(self):
        deps = _make_context()

        mock_result = _make_mock_result(
            output=ConnectedZonesResult(zone_slugs=[]), total_tokens=150,
        )
        deps.discovery_agent.run = AsyncMock(return_value=mock_result)

        ctx = _make_run_context(deps)
        await discover_zones(ctx)

        assert deps.worker_tokens == 150


# ---------------------------------------------------------------------------
# summarize_content
# ---------------------------------------------------------------------------


class TestSummarizeContent:
    @pytest.mark.asyncio
    async def test_summarizes_large_content(self):
        deps = _make_context()
        deps.research_content["npc_research"] = ["A" * 10000, "B" * 10000]

        ctx = _make_run_context(deps)

        with patch("src.orchestrator_tools.mcp_call", new_callable=AsyncMock) as mock_mcp:
            mock_mcp.return_value = "Compressed summary of NPC data"
            result = await summarize_content(ctx, "npc_research")

        assert "Summarized" in result
        assert deps.research_content["npc_research"] == ["Compressed summary of NPC data"]

    @pytest.mark.asyncio
    async def test_no_content_returns_message(self):
        deps = _make_context()

        ctx = _make_run_context(deps)
        result = await summarize_content(ctx, "npc_research")

        assert "No content" in result

    @pytest.mark.asyncio
    async def test_summarization_failure_keeps_original(self):
        deps = _make_context()
        original = ["original content block"]
        deps.research_content["lore_research"] = list(original)

        ctx = _make_run_context(deps)

        with patch("src.orchestrator_tools.mcp_call", new_callable=AsyncMock) as mock_mcp:
            mock_mcp.return_value = None  # Failed
            result = await summarize_content(ctx, "lore_research")

        assert "failed" in result
        assert deps.research_content["lore_research"] == original

    @pytest.mark.asyncio
    async def test_summarization_larger_result_keeps_original(self):
        deps = _make_context()
        deps.research_content["zone_overview_research"] = ["short"]

        ctx = _make_run_context(deps)

        with patch("src.orchestrator_tools.mcp_call", new_callable=AsyncMock) as mock_mcp:
            # Return a result larger than the original
            mock_mcp.return_value = "much longer than the original content"
            result = await summarize_content(ctx, "zone_overview_research")

        assert "failed" in result
        assert deps.research_content["zone_overview_research"] == ["short"]


# ---------------------------------------------------------------------------
# crawl_webpage
# ---------------------------------------------------------------------------


class TestCrawlWebpage:
    @pytest.mark.asyncio
    async def test_crawls_url_and_accumulates(self):
        deps = _make_context()

        ctx = _make_run_context(deps)

        with patch("src.orchestrator_tools.rest_crawl_url", new_callable=AsyncMock) as mock_crawl:
            mock_crawl.return_value = {"content": "Page content here", "error": None}
            result = await crawl_webpage(ctx, "https://wiki.gg/page")

        assert "Page content here" in result
        assert "_direct" in deps.research_content
        assert len(deps.research_content["_direct"]) == 1
        assert len(deps.sources) == 1

    @pytest.mark.asyncio
    async def test_uses_cache(self):
        deps = _make_context(crawl_cache={"https://wiki.gg/page": "cached content"})

        ctx = _make_run_context(deps)
        result = await crawl_webpage(ctx, "https://wiki.gg/page")

        assert "cached content" in result
        assert "_direct" in deps.research_content
        assert len(deps.sources) == 1

    @pytest.mark.asyncio
    async def test_truncates_long_content(self):
        deps = _make_context()
        long_content = "x" * 10000

        ctx = _make_run_context(deps)

        with patch("src.orchestrator_tools.rest_crawl_url", new_callable=AsyncMock) as mock_crawl:
            mock_crawl.return_value = {"content": long_content, "error": None}
            result = await crawl_webpage(ctx, "https://wiki.gg/long")

        # Result should be truncated but full content in deps
        assert "truncated" in result
        assert len(deps.research_content["_direct"][0]) == 10000

    @pytest.mark.asyncio
    async def test_crawl_failure(self):
        deps = _make_context()

        ctx = _make_run_context(deps)

        with patch("src.orchestrator_tools.rest_crawl_url", new_callable=AsyncMock) as mock_crawl:
            mock_crawl.return_value = {"content": None, "error": "timeout"}
            result = await crawl_webpage(ctx, "https://wiki.gg/broken")

        assert "Failed" in result
        assert "_direct" not in deps.research_content

    @pytest.mark.asyncio
    async def test_populates_crawl_cache(self):
        deps = _make_context()

        ctx = _make_run_context(deps)

        with patch("src.orchestrator_tools.rest_crawl_url", new_callable=AsyncMock) as mock_crawl:
            mock_crawl.return_value = {"content": "new page", "error": None}
            await crawl_webpage(ctx, "https://wiki.gg/new")

        assert "https://wiki.gg/new" in deps.crawl_cache


# ---------------------------------------------------------------------------
# Token accumulation across tools
# ---------------------------------------------------------------------------


class TestTokenAccumulation:
    @pytest.mark.asyncio
    async def test_tokens_accumulate_across_multiple_tools(self):
        deps = _make_context()

        # Simulate research
        mock_research = _make_mock_result(total_tokens=500)
        deps.research_agent.run = AsyncMock(return_value=mock_research)

        ctx = _make_run_context(deps)
        await research_topic(ctx, "zone_overview_research")

        # Simulate extraction
        deps.research_content["zone_overview_research"] = ["content"]
        mock_extract = _make_mock_result(
            output=make_zone(name="Test"), total_tokens=200,
        )
        deps.extraction_agents["zone"].run = AsyncMock(return_value=mock_extract)
        await extract_category(ctx, "zone")

        # Simulate cross-reference
        mock_cr = _make_mock_result(
            output=make_cross_ref(confidence={}),
            total_tokens=300,
        )
        deps.cross_ref_agent.run = AsyncMock(return_value=mock_cr)
        await cross_reference(ctx)

        assert deps.worker_tokens == 500 + 200 + 300
