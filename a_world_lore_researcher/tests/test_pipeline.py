"""Tests for the 9-step research pipeline — steps call LoreResearcher, not mcp_client."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agent import (
    CrossReferenceResult,
    LoreResearcher,
    ResearchResult,
    ZoneExtraction,
)
from src.models import (
    MessageEnvelope,
    ResearchCheckpoint,
    SourceReference,
    SourceTier,
    ZoneData,
    NPCData,
    FactionData,
    LoreData,
    NarrativeItemData,
    Conflict,
)
from src.pipeline import (
    PIPELINE_STEPS,
    run_pipeline,
    step_zone_overview_research,
    step_npc_research,
    step_faction_research,
    step_lore_research,
    step_narrative_items_research,
    step_extract_all,
    step_cross_reference,
    step_discover_connected_zones,
    step_package_and_send,
)


# --- Fixtures ---


def _mock_researcher() -> MagicMock:
    """Create a mock LoreResearcher with all methods stubbed."""
    researcher = MagicMock(spec=LoreResearcher)
    researcher.AGENT_ID = "world_lore_researcher"

    researcher.research_zone = AsyncMock(return_value=ResearchResult(
        raw_content=["# Elwynn Forest\nPeaceful starting zone..."],
        sources=[SourceReference(
            url="https://wowpedia.fandom.com/wiki/Elwynn",
            domain="wowpedia.fandom.com",
            tier=SourceTier.OFFICIAL,
        )],
        summary="Researched zone overview.",
    ))

    researcher.extract_zone_data = AsyncMock(return_value=ZoneExtraction(
        zone=ZoneData(name="Elwynn Forest", game="wow", narrative_arc="Starting zone"),
        npcs=[NPCData(name="Marshal Dughan")],
        factions=[FactionData(name="Stormwind Guard")],
        lore=[LoreData(title="History of Elwynn")],
        narrative_items=[NarrativeItemData(name="Hogger's Claw")],
    ))

    researcher.cross_reference = AsyncMock(return_value=CrossReferenceResult(
        is_consistent=True,
        confidence={"zone": 0.9, "npcs": 0.85, "factions": 0.8},
        notes="All consistent.",
    ))

    researcher.discover_connected_zones = AsyncMock(
        return_value=["westfall", "stormwind_city", "redridge_mountains"]
    )

    return researcher


def _fresh_checkpoint() -> ResearchCheckpoint:
    return ResearchCheckpoint(zone_name="elwynn_forest")


# --- Pipeline structure ---


class TestPipelineSteps:
    def test_pipeline_has_9_steps(self):
        assert len(PIPELINE_STEPS) == 9

    def test_step_names(self):
        expected = [
            "zone_overview_research",
            "npc_research",
            "faction_research",
            "lore_research",
            "narrative_items_research",
            "extract_all",
            "cross_reference",
            "discover_connected_zones",
            "package_and_send",
        ]
        assert PIPELINE_STEPS == expected


# --- Steps 1-5: Research ---


class TestResearchSteps:
    @pytest.mark.asyncio
    async def test_zone_overview_accumulates(self):
        cp = _fresh_checkpoint()
        researcher = _mock_researcher()
        await step_zone_overview_research(cp, researcher)

        assert len(cp.step_data["research_raw_content"]) == 1
        assert len(cp.step_data["research_sources"]) == 1
        researcher.research_zone.assert_called_once()

    @pytest.mark.asyncio
    async def test_npc_research_accumulates(self):
        cp = _fresh_checkpoint()
        researcher = _mock_researcher()
        # Simulate step 1 already ran
        cp.step_data["research_raw_content"] = ["existing content"]
        cp.step_data["research_sources"] = [{"url": "https://x.com", "domain": "x.com", "tier": "official", "accessed_at": "2026-01-01T00:00:00"}]

        await step_npc_research(cp, researcher)

        assert len(cp.step_data["research_raw_content"]) == 2
        assert len(cp.step_data["research_sources"]) == 2

    @pytest.mark.asyncio
    async def test_faction_research(self):
        cp = _fresh_checkpoint()
        researcher = _mock_researcher()
        await step_faction_research(cp, researcher)
        assert "research_raw_content" in cp.step_data
        researcher.research_zone.assert_called_once()

    @pytest.mark.asyncio
    async def test_lore_research(self):
        cp = _fresh_checkpoint()
        researcher = _mock_researcher()
        await step_lore_research(cp, researcher)
        assert "research_raw_content" in cp.step_data

    @pytest.mark.asyncio
    async def test_narrative_items_research(self):
        cp = _fresh_checkpoint()
        researcher = _mock_researcher()
        await step_narrative_items_research(cp, researcher)
        assert "research_raw_content" in cp.step_data


# --- Step 6: Extract all ---


class TestExtractAll:
    @pytest.mark.asyncio
    async def test_stores_extraction(self):
        cp = _fresh_checkpoint()
        cp.step_data["research_raw_content"] = ["raw content here"]
        cp.step_data["research_sources"] = [
            {"url": "https://wowpedia.fandom.com/wiki/Elwynn", "domain": "wowpedia.fandom.com", "tier": "official", "accessed_at": "2026-01-01T00:00:00"},
        ]
        researcher = _mock_researcher()

        await step_extract_all(cp, researcher)

        assert "extraction" in cp.step_data
        extraction = ZoneExtraction.model_validate(cp.step_data["extraction"])
        assert extraction.zone.name == "Elwynn Forest"
        assert len(extraction.npcs) == 1
        researcher.extract_zone_data.assert_called_once()


# --- Step 7: Cross-reference ---


class TestCrossReference:
    @pytest.mark.asyncio
    async def test_stores_cross_reference(self):
        cp = _fresh_checkpoint()
        extraction = ZoneExtraction(
            zone=ZoneData(name="Elwynn Forest"),
            npcs=[NPCData(name="Marshal Dughan")],
        )
        cp.step_data["extraction"] = extraction.model_dump(mode="json")
        researcher = _mock_researcher()

        await step_cross_reference(cp, researcher)

        assert "cross_reference" in cp.step_data
        cr = CrossReferenceResult.model_validate(cp.step_data["cross_reference"])
        assert cr.is_consistent is True
        assert cr.confidence["zone"] == 0.9
        researcher.cross_reference.assert_called_once()


# --- Step 8: Discover connected zones ---


class TestDiscoverConnectedZones:
    @pytest.mark.asyncio
    async def test_populates_progression_queue(self):
        cp = _fresh_checkpoint()
        researcher = _mock_researcher()

        await step_discover_connected_zones(cp, researcher)

        assert "westfall" in cp.progression_queue
        assert "stormwind_city" in cp.progression_queue
        assert "redridge_mountains" in cp.progression_queue
        assert cp.step_data["discovered_zones"] == ["westfall", "stormwind_city", "redridge_mountains"]

    @pytest.mark.asyncio
    async def test_filters_completed_zones(self):
        cp = _fresh_checkpoint()
        cp.completed_zones = ["westfall"]
        researcher = _mock_researcher()

        await step_discover_connected_zones(cp, researcher)

        assert "westfall" not in cp.progression_queue
        assert "stormwind_city" in cp.progression_queue

    @pytest.mark.asyncio
    async def test_filters_current_zone(self):
        cp = ResearchCheckpoint(zone_name="westfall")
        researcher = _mock_researcher()
        researcher.discover_connected_zones = AsyncMock(
            return_value=["westfall", "elwynn_forest"]
        )

        await step_discover_connected_zones(cp, researcher)

        assert "westfall" not in cp.progression_queue
        assert "elwynn_forest" in cp.progression_queue


# --- Step 9: Package and send ---


class TestPackageAndSend:
    def _setup_checkpoint(self) -> ResearchCheckpoint:
        """Create checkpoint with steps 6-7 data already populated."""
        cp = _fresh_checkpoint()
        extraction = ZoneExtraction(
            zone=ZoneData(name="Elwynn Forest", game="wow"),
            npcs=[NPCData(name="Marshal Dughan")],
            factions=[FactionData(name="Stormwind Guard")],
        )
        cr_result = CrossReferenceResult(
            is_consistent=True,
            confidence={"zone": 0.9, "npcs": 0.85},
        )
        cp.step_data["extraction"] = extraction.model_dump(mode="json")
        cp.step_data["cross_reference"] = cr_result.model_dump(mode="json")
        cp.step_data["research_sources"] = [
            {"url": "https://wowpedia.fandom.com/wiki/Elwynn", "domain": "wowpedia.fandom.com", "tier": "official", "accessed_at": "2026-01-01T00:00:00"},
        ]
        return cp

    @pytest.mark.asyncio
    async def test_assembles_full_package(self):
        cp = self._setup_checkpoint()
        researcher = _mock_researcher()

        await step_package_and_send(cp, researcher)

        assert "package" in cp.step_data
        pkg = cp.step_data["package"]
        assert pkg["zone_name"] == "elwynn_forest"
        assert pkg["zone_data"]["name"] == "Elwynn Forest"
        assert len(pkg["npcs"]) == 1
        assert len(pkg["factions"]) == 1
        assert len(pkg["sources"]) == 1
        assert pkg["confidence"]["zone"] == 0.9

    @pytest.mark.asyncio
    async def test_calls_publish_fn(self):
        cp = self._setup_checkpoint()
        researcher = _mock_researcher()
        publish_fn = AsyncMock()

        await step_package_and_send(cp, researcher, publish_fn)

        publish_fn.assert_called_once()
        envelope = publish_fn.call_args[0][0]
        assert isinstance(envelope, MessageEnvelope)
        assert envelope.source_agent == "world_lore_researcher"
        assert envelope.target_agent == "world_lore_validator"
        assert envelope.message_type.value == "research_package"

    @pytest.mark.asyncio
    async def test_handles_no_publish_fn(self):
        cp = self._setup_checkpoint()
        researcher = _mock_researcher()

        # Should not raise even without publish_fn
        await step_package_and_send(cp, researcher, None)
        assert "package" in cp.step_data


# --- Full pipeline ---


class TestRunPipeline:
    @pytest.mark.asyncio
    async def test_runs_all_steps(self):
        cp = _fresh_checkpoint()
        researcher = _mock_researcher()
        publish_fn = AsyncMock()

        with pytest.MonkeyPatch.context() as m:
            m.setattr("src.pipeline.save_checkpoint", AsyncMock())

            result = await run_pipeline(cp, researcher, publish_fn)

        assert result.current_step == 9
        assert "package" in result.step_data
        assert result.step_data["package"]["zone_name"] == "elwynn_forest"
        publish_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_resumes_from_checkpoint(self):
        cp = _fresh_checkpoint()
        cp.current_step = 7  # Start at discover_connected_zones

        researcher = _mock_researcher()

        with pytest.MonkeyPatch.context() as m:
            save_mock = AsyncMock()
            m.setattr("src.pipeline.save_checkpoint", save_mock)

            # Need extraction + cross_reference data for package_and_send
            extraction = ZoneExtraction(
                zone=ZoneData(name="Elwynn Forest", game="wow"),
            )
            cr_result = CrossReferenceResult(is_consistent=True, confidence={"zone": 0.9})
            cp.step_data["extraction"] = extraction.model_dump(mode="json")
            cp.step_data["cross_reference"] = cr_result.model_dump(mode="json")
            cp.step_data["research_sources"] = []

            result = await run_pipeline(cp, researcher)

        assert result.current_step == 9
        # Only steps 8 and 9 should have saved (indices 7 and 8)
        assert save_mock.call_count == 2
