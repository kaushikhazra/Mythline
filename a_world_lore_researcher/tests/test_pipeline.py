"""Tests for the 10-step research pipeline — individual steps with mocked MCP calls."""

from unittest.mock import AsyncMock, patch

import pytest

from src.models import ResearchCheckpoint
from src.pipeline import (
    PIPELINE_STEPS,
    _make_source_ref,
    step_zone_overview_search,
    step_zone_overview_extract,
    step_npc_search,
    step_npc_extract,
    step_faction_search_extract,
    step_lore_search_extract,
    step_narrative_items_search_extract,
    step_cross_reference,
    step_discover_connected_zones,
    step_package_and_send,
    run_pipeline,
)


MOCK_SEARCH_RESULTS = [
    {"title": "Elwynn Forest - Wowpedia", "url": "https://wowpedia.fandom.com/wiki/Elwynn_Forest", "snippet": "Elwynn Forest..."},
    {"title": "Elwynn Forest - Warcraft Wiki", "url": "https://warcraft.wiki.gg/wiki/Elwynn_Forest", "snippet": "Zone guide..."},
]

MOCK_CRAWL_RESULT = {
    "url": "https://wowpedia.fandom.com/wiki/Elwynn_Forest",
    "title": "Elwynn Forest",
    "content": "# Elwynn Forest\n\nA peaceful forest in the Eastern Kingdoms...",
    "error": None,
}


class TestPipelineSteps:
    def test_pipeline_has_10_steps(self):
        assert len(PIPELINE_STEPS) == 10

    def test_make_source_ref_known_domain(self):
        ref = _make_source_ref("https://wowpedia.fandom.com/wiki/Elwynn")
        assert ref.domain == "wowpedia.fandom.com"

    def test_make_source_ref_unknown_domain(self):
        ref = _make_source_ref("https://unknown-site.com/page")
        assert ref.domain == "unknown-site.com"


class TestZoneOverviewSearch:
    @pytest.mark.asyncio
    @patch("src.pipeline.web_search", new_callable=AsyncMock, return_value=MOCK_SEARCH_RESULTS)
    async def test_collects_urls(self, mock_search):
        cp = ResearchCheckpoint(zone_name="elwynn_forest")
        result = await step_zone_overview_search(cp)
        assert len(result.step_data["zone_overview_urls"]) == 2
        assert "wowpedia.fandom.com" in result.step_data["zone_overview_urls"][0]


class TestZoneOverviewExtract:
    @pytest.mark.asyncio
    @patch("src.pipeline.crawl_url", new_callable=AsyncMock, return_value=MOCK_CRAWL_RESULT)
    async def test_crawls_and_stores_content(self, mock_crawl):
        cp = ResearchCheckpoint(zone_name="elwynn_forest")
        cp.step_data["zone_overview_urls"] = ["https://wowpedia.fandom.com/wiki/Elwynn_Forest"]
        result = await step_zone_overview_extract(cp)
        assert len(result.step_data["zone_overview_content"]) == 1
        assert "Elwynn Forest" in result.step_data["zone_overview_content"][0]
        assert len(result.step_data["zone_overview_sources"]) == 1

    @pytest.mark.asyncio
    @patch("src.pipeline.crawl_url", new_callable=AsyncMock, return_value={"url": "x", "content": None, "error": "fail"})
    async def test_skips_failed_crawls(self, mock_crawl):
        cp = ResearchCheckpoint(zone_name="elwynn_forest")
        cp.step_data["zone_overview_urls"] = ["https://example.com"]
        result = await step_zone_overview_extract(cp)
        assert len(result.step_data["zone_overview_content"]) == 0


class TestNPCSteps:
    @pytest.mark.asyncio
    @patch("src.pipeline.web_search", new_callable=AsyncMock, return_value=MOCK_SEARCH_RESULTS)
    async def test_npc_search(self, mock_search):
        cp = ResearchCheckpoint(zone_name="elwynn_forest")
        result = await step_npc_search(cp)
        assert "npc_urls" in result.step_data

    @pytest.mark.asyncio
    @patch("src.pipeline.crawl_url", new_callable=AsyncMock, return_value=MOCK_CRAWL_RESULT)
    async def test_npc_extract(self, mock_crawl):
        cp = ResearchCheckpoint(zone_name="elwynn_forest")
        cp.step_data["npc_urls"] = ["https://example.com/npcs"]
        result = await step_npc_extract(cp)
        assert len(result.step_data["npc_content"]) == 1


class TestFactionStep:
    @pytest.mark.asyncio
    @patch("src.pipeline.crawl_url", new_callable=AsyncMock, return_value=MOCK_CRAWL_RESULT)
    @patch("src.pipeline.web_search", new_callable=AsyncMock, return_value=MOCK_SEARCH_RESULTS)
    async def test_faction_search_extract(self, mock_search, mock_crawl):
        cp = ResearchCheckpoint(zone_name="elwynn_forest")
        result = await step_faction_search_extract(cp)
        assert "faction_content" in result.step_data
        assert len(result.step_data["faction_content"]) > 0


class TestLoreStep:
    @pytest.mark.asyncio
    @patch("src.pipeline.crawl_url", new_callable=AsyncMock, return_value=MOCK_CRAWL_RESULT)
    @patch("src.pipeline.web_search", new_callable=AsyncMock, return_value=MOCK_SEARCH_RESULTS)
    async def test_lore_search_extract(self, mock_search, mock_crawl):
        cp = ResearchCheckpoint(zone_name="elwynn_forest")
        result = await step_lore_search_extract(cp)
        assert "lore_content" in result.step_data


class TestNarrativeItemsStep:
    @pytest.mark.asyncio
    @patch("src.pipeline.crawl_url", new_callable=AsyncMock, return_value=MOCK_CRAWL_RESULT)
    @patch("src.pipeline.web_search", new_callable=AsyncMock, return_value=MOCK_SEARCH_RESULTS)
    async def test_narrative_items(self, mock_search, mock_crawl):
        cp = ResearchCheckpoint(zone_name="elwynn_forest")
        result = await step_narrative_items_search_extract(cp)
        assert "narrative_items_content" in result.step_data


class TestCrossReference:
    @pytest.mark.asyncio
    async def test_marks_complete(self):
        cp = ResearchCheckpoint(zone_name="elwynn_forest")
        result = await step_cross_reference(cp)
        assert result.step_data["cross_reference_complete"] is True


class TestDiscoverConnectedZones:
    @pytest.mark.asyncio
    @patch("src.pipeline.web_search", new_callable=AsyncMock, return_value=MOCK_SEARCH_RESULTS)
    async def test_discovers_zones(self, mock_search):
        cp = ResearchCheckpoint(zone_name="elwynn_forest")
        result = await step_discover_connected_zones(cp)
        assert result.step_data["discover_connected_complete"] is True


class TestPackageAndSend:
    @pytest.mark.asyncio
    async def test_creates_package(self):
        cp = ResearchCheckpoint(zone_name="elwynn_forest")
        cp.step_data["zone_overview_sources"] = [
            {"url": "https://wowpedia.fandom.com/wiki/Elwynn", "domain": "wowpedia.fandom.com", "tier": "official", "accessed_at": "2026-02-21T00:00:00"},
        ]
        cp.step_data["npc_sources"] = []
        cp.step_data["faction_sources"] = []
        cp.step_data["lore_sources"] = []
        cp.step_data["narrative_items_sources"] = []

        result = await step_package_and_send(cp)
        assert result.step_data["package_ready"] is True
        assert result.step_data["package"]["zone_name"] == "elwynn_forest"
        assert len(result.step_data["package"]["sources"]) == 1


class TestRunPipeline:
    @pytest.mark.asyncio
    @patch("src.pipeline.save_checkpoint", new_callable=AsyncMock)
    @patch("src.pipeline.crawl_url", new_callable=AsyncMock, return_value=MOCK_CRAWL_RESULT)
    @patch("src.pipeline.web_search", new_callable=AsyncMock, return_value=MOCK_SEARCH_RESULTS)
    async def test_runs_all_steps(self, mock_search, mock_crawl, mock_save):
        cp = ResearchCheckpoint(zone_name="elwynn_forest")
        result = await run_pipeline(cp)
        assert result.current_step == 10
        assert mock_save.call_count == 10
        assert result.step_data["package_ready"] is True

    @pytest.mark.asyncio
    @patch("src.pipeline.save_checkpoint", new_callable=AsyncMock)
    @patch("src.pipeline.crawl_url", new_callable=AsyncMock, return_value=MOCK_CRAWL_RESULT)
    @patch("src.pipeline.web_search", new_callable=AsyncMock, return_value=MOCK_SEARCH_RESULTS)
    async def test_resumes_from_checkpoint(self, mock_search, mock_crawl, mock_save):
        cp = ResearchCheckpoint(zone_name="elwynn_forest", current_step=7)
        cp.step_data["zone_overview_sources"] = []
        cp.step_data["npc_sources"] = []
        cp.step_data["faction_sources"] = []
        cp.step_data["lore_sources"] = []
        cp.step_data["narrative_items_sources"] = []

        result = await run_pipeline(cp)
        assert result.current_step == 10
        assert mock_save.call_count == 3
