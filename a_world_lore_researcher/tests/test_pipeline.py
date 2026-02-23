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
    TOPIC_SECTION_HEADERS,
    _reconstruct_labeled_content,
    _summarize_research_result,
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
    return ResearchCheckpoint(job_id="test-job", zone_name="elwynn_forest")


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
    async def test_zone_overview_accumulates_with_topic_label(self):
        cp = _fresh_checkpoint()
        researcher = _mock_researcher()
        await step_zone_overview_research(cp, researcher)

        raw = cp.step_data["research_raw_content"]
        assert len(raw) == 1
        assert raw[0]["topic"] == "zone_overview_research"
        assert raw[0]["content"] == "# Elwynn Forest\nPeaceful starting zone..."
        assert len(cp.step_data["research_sources"]) == 1
        researcher.research_zone.assert_called_once()

    @pytest.mark.asyncio
    async def test_npc_research_accumulates_with_topic_label(self):
        cp = _fresh_checkpoint()
        researcher = _mock_researcher()
        # Simulate step 1 already ran (labeled format)
        cp.step_data["research_raw_content"] = [
            {"topic": "zone_overview_research", "content": "existing content"}
        ]
        cp.step_data["research_sources"] = [{"url": "https://x.com", "domain": "x.com", "tier": "official", "accessed_at": "2026-01-01T00:00:00"}]

        await step_npc_research(cp, researcher)

        raw = cp.step_data["research_raw_content"]
        assert len(raw) == 2
        assert raw[0]["topic"] == "zone_overview_research"
        assert raw[1]["topic"] == "npc_research"
        assert len(cp.step_data["research_sources"]) == 2

    @pytest.mark.asyncio
    async def test_faction_research_labels_topic(self):
        cp = _fresh_checkpoint()
        researcher = _mock_researcher()
        await step_faction_research(cp, researcher)

        raw = cp.step_data["research_raw_content"]
        assert len(raw) == 1
        assert raw[0]["topic"] == "faction_research"
        researcher.research_zone.assert_called_once()

    @pytest.mark.asyncio
    async def test_lore_research_labels_topic(self):
        cp = _fresh_checkpoint()
        researcher = _mock_researcher()
        await step_lore_research(cp, researcher)

        raw = cp.step_data["research_raw_content"]
        assert raw[0]["topic"] == "lore_research"

    @pytest.mark.asyncio
    async def test_narrative_items_research_labels_topic(self):
        cp = _fresh_checkpoint()
        researcher = _mock_researcher()
        await step_narrative_items_research(cp, researcher)

        raw = cp.step_data["research_raw_content"]
        assert raw[0]["topic"] == "narrative_items_research"


# --- Step 6: Extract all ---


class TestExtractAll:
    @pytest.mark.asyncio
    async def test_stores_extraction_from_labeled_content(self):
        cp = _fresh_checkpoint()
        cp.step_data["research_raw_content"] = [
            {"topic": "zone_overview_research", "content": "Elwynn Forest is a peaceful zone."},
            {"topic": "npc_research", "content": "Marshal Dughan guards Goldshire."},
            {"topic": "faction_research", "content": "Stormwind Guard patrols the area."},
        ]
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

        # Verify labeled sections were reconstructed with headers
        call_args = researcher.extract_zone_data.call_args
        raw_content_arg = call_args[0][1]  # second positional arg
        assert len(raw_content_arg) == 3
        assert raw_content_arg[0].startswith("## ZONE OVERVIEW")
        assert raw_content_arg[1].startswith("## NPCs AND NOTABLE CHARACTERS")
        assert raw_content_arg[2].startswith("## FACTIONS AND ORGANIZATIONS")


# --- Labeled content reconstruction ---


class TestReconstructLabeledContent:
    def test_groups_by_topic_with_headers(self):
        blocks = [
            {"topic": "zone_overview_research", "content": "Zone info here."},
            {"topic": "npc_research", "content": "NPC info here."},
            {"topic": "zone_overview_research", "content": "More zone info."},
        ]
        sections = _reconstruct_labeled_content(blocks)

        assert len(sections) == 2
        assert sections[0].startswith("## ZONE OVERVIEW")
        assert "Zone info here." in sections[0]
        assert "More zone info." in sections[0]
        assert sections[1].startswith("## NPCs AND NOTABLE CHARACTERS")
        assert "NPC info here." in sections[1]

    def test_preserves_topic_order(self):
        blocks = [
            {"topic": "npc_research", "content": "NPCs first."},
            {"topic": "zone_overview_research", "content": "Zone second."},
        ]
        sections = _reconstruct_labeled_content(blocks)

        assert len(sections) == 2
        # NPC came first in input, should be first in output
        assert sections[0].startswith("## NPCs AND NOTABLE CHARACTERS")
        assert sections[1].startswith("## ZONE OVERVIEW")

    def test_all_five_topics(self):
        blocks = [
            {"topic": "zone_overview_research", "content": "zone"},
            {"topic": "npc_research", "content": "npcs"},
            {"topic": "faction_research", "content": "factions"},
            {"topic": "lore_research", "content": "lore"},
            {"topic": "narrative_items_research", "content": "items"},
        ]
        sections = _reconstruct_labeled_content(blocks)

        assert len(sections) == 5
        headers = [s.split("\n")[0] for s in sections]
        assert headers == [
            TOPIC_SECTION_HEADERS["zone_overview_research"],
            TOPIC_SECTION_HEADERS["npc_research"],
            TOPIC_SECTION_HEADERS["faction_research"],
            TOPIC_SECTION_HEADERS["lore_research"],
            TOPIC_SECTION_HEADERS["narrative_items_research"],
        ]

    def test_empty_blocks(self):
        assert _reconstruct_labeled_content([]) == []

    def test_unknown_topic_gets_fallback_header(self):
        blocks = [{"topic": "mystery_topic", "content": "data"}]
        sections = _reconstruct_labeled_content(blocks)

        assert len(sections) == 1
        assert sections[0].startswith("## MYSTERY_TOPIC")


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


# --- Step 8: Discover connected zones (pure discovery) ---


class TestDiscoverConnectedZones:
    @pytest.mark.asyncio
    async def test_writes_discovered_zones_to_step_data(self):
        cp = _fresh_checkpoint()
        researcher = _mock_researcher()

        await step_discover_connected_zones(cp, researcher)

        assert cp.step_data["discovered_zones"] == ["westfall", "stormwind_city", "redridge_mountains"]

    @pytest.mark.asyncio
    async def test_no_filtering(self):
        """Step 8 is pure discovery — no filtering against completed/pending zones."""
        cp = _fresh_checkpoint()
        researcher = _mock_researcher()

        await step_discover_connected_zones(cp, researcher)

        # All discovered zones are stored, even if they overlap
        assert len(cp.step_data["discovered_zones"]) == 3


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

    @pytest.mark.asyncio
    async def test_skip_steps(self):
        """Skipped steps log and advance without executing."""
        cp = _fresh_checkpoint()
        researcher = _mock_researcher()

        with pytest.MonkeyPatch.context() as m:
            save_mock = AsyncMock()
            m.setattr("src.pipeline.save_checkpoint", save_mock)

            result = await run_pipeline(
                cp, researcher,
                skip_steps={"discover_connected_zones"},
            )

        assert result.current_step == 9
        # discover_connected_zones was skipped — no discovered_zones in step_data
        assert "discovered_zones" not in result.step_data
        # research_zone should have been called 5 times (steps 1-5)
        assert researcher.research_zone.call_count == 5
        # discover_connected_zones should NOT have been called
        researcher.discover_connected_zones.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_multiple_steps(self):
        """Multiple steps can be skipped."""
        cp = _fresh_checkpoint()
        cp.current_step = 5  # Start at extract_all (step 6)

        researcher = _mock_researcher()

        with pytest.MonkeyPatch.context() as m:
            save_mock = AsyncMock()
            m.setattr("src.pipeline.save_checkpoint", save_mock)

            # Pre-populate required step_data (labeled format)
            cp.step_data["research_raw_content"] = [
                {"topic": "zone_overview_research", "content": "raw"}
            ]
            cp.step_data["research_sources"] = []
            extraction = ZoneExtraction(zone=ZoneData(name="Elwynn Forest"))
            cp.step_data["extraction"] = extraction.model_dump(mode="json")
            cr_result = CrossReferenceResult(is_consistent=True, confidence={"zone": 0.9})
            cp.step_data["cross_reference"] = cr_result.model_dump(mode="json")

            result = await run_pipeline(
                cp, researcher,
                skip_steps={"extract_all", "cross_reference", "discover_connected_zones"},
            )

        assert result.current_step == 9
        # extract_all and cross_reference were skipped — originals still in step_data
        researcher.extract_zone_data.assert_not_called()
        researcher.cross_reference.assert_not_called()
        researcher.discover_connected_zones.assert_not_called()

    @pytest.mark.asyncio
    async def test_step_progress_callback(self):
        """on_step_progress callback fires after each step (including skipped)."""
        cp = _fresh_checkpoint()
        cp.current_step = 7  # Start at discover_connected_zones (step 8)

        researcher = _mock_researcher()
        progress_calls: list[tuple[str, int, int]] = []

        async def on_progress(step_name: str, step_number: int, total_steps: int):
            progress_calls.append((step_name, step_number, total_steps))

        with pytest.MonkeyPatch.context() as m:
            m.setattr("src.pipeline.save_checkpoint", AsyncMock())

            extraction = ZoneExtraction(zone=ZoneData(name="Elwynn Forest"))
            cr_result = CrossReferenceResult(is_consistent=True, confidence={"zone": 0.9})
            cp.step_data["extraction"] = extraction.model_dump(mode="json")
            cp.step_data["cross_reference"] = cr_result.model_dump(mode="json")
            cp.step_data["research_sources"] = []

            await run_pipeline(
                cp, researcher,
                skip_steps={"discover_connected_zones"},
                on_step_progress=on_progress,
            )

        # Steps 8 (skipped) and 9 (executed) should fire callback
        assert len(progress_calls) == 2
        assert progress_calls[0] == ("discover_connected_zones", 8, 9)
        assert progress_calls[1] == ("package_and_send", 9, 9)


# --- _summarize_research_result ---


class TestSummarizeResearchResult:
    @pytest.mark.asyncio
    async def test_returns_original_when_url_empty(self):
        """When MCP_SUMMARIZER_URL is empty, return result unchanged."""
        result = ResearchResult(
            raw_content=["Block 1", "Block 2"],
            sources=[SourceReference(
                url="https://example.com",
                domain="example.com",
                tier=SourceTier.OFFICIAL,
            )],
            summary="Summary.",
        )

        with pytest.MonkeyPatch.context() as m:
            m.setattr("src.pipeline.MCP_SUMMARIZER_URL", "")
            output = await _summarize_research_result(result, "zone_overview_research", "elwynn forest")

        assert output is result

    @pytest.mark.asyncio
    async def test_returns_original_when_no_raw_content(self):
        """When raw_content is empty, return result unchanged."""
        result = ResearchResult(raw_content=[], sources=[], summary="")

        with pytest.MonkeyPatch.context() as m:
            m.setattr("src.pipeline.MCP_SUMMARIZER_URL", "http://localhost:8007/mcp")
            output = await _summarize_research_result(result, "npc_research", "elwynn forest")

        assert output is result

    @pytest.mark.asyncio
    async def test_returns_original_on_mcp_call_failure(self):
        """When mcp_call returns None, return original result unchanged."""
        result = ResearchResult(
            raw_content=["Content block."],
            sources=[SourceReference(
                url="https://example.com",
                domain="example.com",
                tier=SourceTier.OFFICIAL,
            )],
            summary="Summary.",
        )

        with pytest.MonkeyPatch.context() as m:
            m.setattr("src.pipeline.MCP_SUMMARIZER_URL", "http://localhost:8007/mcp")
            m.setattr("src.pipeline.mcp_call", AsyncMock(return_value=None))
            output = await _summarize_research_result(result, "zone_overview_research", "elwynn forest")

        assert output is result
        assert output.raw_content == ["Content block."]

    @pytest.mark.asyncio
    async def test_replaces_raw_content_with_summary(self):
        """On success, raw_content should be replaced with single summary block."""
        result = ResearchResult(
            raw_content=["Block 1", "Block 2", "Block 3"],
            sources=[SourceReference(
                url="https://example.com",
                domain="example.com",
                tier=SourceTier.OFFICIAL,
            )],
            summary="Original summary.",
        )

        mock_mcp = AsyncMock(return_value="Compressed summary of all blocks.")

        with pytest.MonkeyPatch.context() as m:
            m.setattr("src.pipeline.MCP_SUMMARIZER_URL", "http://localhost:8007/mcp")
            m.setattr("src.pipeline.mcp_call", mock_mcp)
            output = await _summarize_research_result(result, "zone_overview_research", "elwynn forest")

        assert output.raw_content == ["Compressed summary of all blocks."]
        assert output.sources == result.sources
        assert output.summary == result.summary

        # Verify mcp_call was called with correct arguments
        call_kwargs = mock_mcp.call_args
        assert call_kwargs[0][1] == "summarize_for_extraction"
        assert "content" in call_kwargs[0][2]
        assert "schema_hint" in call_kwargs[0][2]

    @pytest.mark.asyncio
    async def test_concatenates_raw_blocks_with_separator(self):
        """Raw content blocks should be joined with --- separator."""
        result = ResearchResult(
            raw_content=["Block A", "Block B"],
            sources=[],
            summary="",
        )

        mock_mcp = AsyncMock(return_value="Summary.")

        with pytest.MonkeyPatch.context() as m:
            m.setattr("src.pipeline.MCP_SUMMARIZER_URL", "http://localhost:8007/mcp")
            m.setattr("src.pipeline.mcp_call", mock_mcp)
            await _summarize_research_result(result, "npc_research", "elwynn forest")

        content_arg = mock_mcp.call_args[0][2]["content"]
        assert "Block A" in content_arg
        assert "Block B" in content_arg
        assert "---" in content_arg

    @pytest.mark.asyncio
    async def test_passes_topic_schema_hint(self):
        """schema_hint should be formatted with zone and game names."""
        result = ResearchResult(raw_content=["Data."], sources=[], summary="")
        mock_mcp = AsyncMock(return_value="Summary.")

        with pytest.MonkeyPatch.context() as m:
            m.setattr("src.pipeline.MCP_SUMMARIZER_URL", "http://localhost:8007/mcp")
            m.setattr("src.pipeline.mcp_call", mock_mcp)
            await _summarize_research_result(result, "faction_research", "elwynn forest")

        schema_hint = mock_mcp.call_args[0][2]["schema_hint"]
        assert "factions" in schema_hint.lower()
        assert "elwynn forest" in schema_hint
        assert "{zone}" not in schema_hint
        assert "{game}" not in schema_hint
