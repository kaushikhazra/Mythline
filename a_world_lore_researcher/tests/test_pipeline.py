"""Tests for the 9-step research pipeline — steps call LoreResearcher, not mcp_client."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agent import (
    CrossReferenceResult,
    FactionExtractionResult,
    LoreExtractionResult,
    LoreResearcher,
    NPCExtractionResult,
    NarrativeItemExtractionResult,
    ResearchResult,
    ZoneExtraction,
)
from src.models import (
    FactionRelation,
    FactionStance,
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
    RESEARCH_TOPICS,
    TOPIC_SCHEMA_HINTS,
    TOPIC_SECTION_HEADERS,
    _apply_confidence_caps,
    _compute_quality_warnings,
    _reconstruct_labeled_content,
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

    # Per-category extraction results
    async def _fake_extract_category(category, zone_name, content, sources):
        results = {
            "zone": ZoneData(name="Elwynn Forest", game="wow", narrative_arc="Starting zone"),
            "npcs": NPCExtractionResult(npcs=[NPCData(name="Marshal Dughan")]),
            "factions": FactionExtractionResult(factions=[FactionData(name="Stormwind Guard")]),
            "lore": LoreExtractionResult(lore=[LoreData(title="History of Elwynn")]),
            "narrative_items": NarrativeItemExtractionResult(
                narrative_items=[NarrativeItemData(name="Hogger's Claw")]
            ),
        }
        return results[category]

    researcher.extract_category = AsyncMock(side_effect=_fake_extract_category)

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
    async def test_calls_extract_category_five_times(self):
        cp = _fresh_checkpoint()
        cp.step_data["research_raw_content"] = [
            {"topic": "zone_overview_research", "content": "Elwynn Forest is a peaceful zone."},
            {"topic": "npc_research", "content": "Marshal Dughan guards Goldshire."},
            {"topic": "faction_research", "content": "Stormwind Guard patrols the area."},
            {"topic": "lore_research", "content": "History of the zone."},
            {"topic": "narrative_items_research", "content": "Hogger's Claw is notable."},
        ]
        cp.step_data["research_sources"] = [
            {"url": "https://wowpedia.fandom.com/wiki/Elwynn", "domain": "wowpedia.fandom.com", "tier": "official", "accessed_at": "2026-01-01T00:00:00"},
        ]
        researcher = _mock_researcher()

        await step_extract_all(cp, researcher)

        assert researcher.extract_category.call_count == 5
        categories_called = [call[0][0] for call in researcher.extract_category.call_args_list]
        assert categories_called == ["zone", "npcs", "factions", "lore", "narrative_items"]

    @pytest.mark.asyncio
    async def test_assembles_zone_extraction(self):
        cp = _fresh_checkpoint()
        cp.step_data["research_raw_content"] = [
            {"topic": "zone_overview_research", "content": "Zone content."},
            {"topic": "npc_research", "content": "NPC content."},
            {"topic": "faction_research", "content": "Faction content."},
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
        assert extraction.npcs[0].name == "Marshal Dughan"
        assert len(extraction.factions) == 1
        assert len(extraction.lore) == 1
        assert len(extraction.narrative_items) == 1

    @pytest.mark.asyncio
    async def test_passes_correct_content_per_category(self):
        cp = _fresh_checkpoint()
        cp.step_data["research_raw_content"] = [
            {"topic": "zone_overview_research", "content": "Zone info here."},
            {"topic": "npc_research", "content": "NPC info here."},
        ]
        cp.step_data["research_sources"] = []
        researcher = _mock_researcher()

        await step_extract_all(cp, researcher)

        # Zone call should get zone content with header
        zone_call = researcher.extract_category.call_args_list[0]
        assert "## ZONE OVERVIEW" in zone_call[0][2]
        assert "Zone info here." in zone_call[0][2]

        # NPC call should get npc content with header
        npc_call = researcher.extract_category.call_args_list[1]
        assert "## NPCs AND NOTABLE CHARACTERS" in npc_call[0][2]
        assert "NPC info here." in npc_call[0][2]

        # Faction call gets empty string (no faction topic in raw content)
        faction_call = researcher.extract_category.call_args_list[2]
        assert faction_call[0][2] == ""


# --- RESEARCH_TOPICS content ---


class TestResearchTopics:
    def test_has_five_topics(self):
        assert len(RESEARCH_TOPICS) == 5

    def test_zone_overview_has_two_phases(self):
        topic = RESEARCH_TOPICS["zone_overview_research"]
        assert "Phase 1" in topic
        assert "Phase 2" in topic

    def test_npc_research_has_hostile_emphasis(self):
        topic = RESEARCH_TOPICS["npc_research"]
        assert "hostile NPCs" in topic
        assert "bosses" in topic.lower()
        assert "antagonist" in topic.lower()

    def test_faction_research_has_hostile_emphasis(self):
        topic = RESEARCH_TOPICS["faction_research"]
        assert "hostile factions" in topic
        assert "enemy factions" in topic
        assert "criminal" in topic.lower()

    def test_all_topics_have_format_placeholders(self):
        for key, topic in RESEARCH_TOPICS.items():
            assert "{zone}" in topic, f"{key} missing {{zone}}"
            assert "{game}" in topic, f"{key} missing {{game}}"

    def test_narrative_items_has_significance_filter(self):
        topic = RESEARCH_TOPICS["narrative_items_research"]
        assert "NOT crafting recipes" in topic
        assert "empty result" in topic.lower()


# --- TOPIC_SCHEMA_HINTS content ---


class TestTopicSchemaHints:
    def test_has_five_hints(self):
        assert len(TOPIC_SCHEMA_HINTS) == 5

    def test_all_hints_have_must_preserve(self):
        for key, hint in TOPIC_SCHEMA_HINTS.items():
            assert "MUST PRESERVE" in hint, f"{key} missing MUST PRESERVE"

    def test_npc_hints_preserve_personality(self):
        hint = TOPIC_SCHEMA_HINTS["npc_research"]
        assert "personality" in hint.lower()
        assert "motivations" in hint.lower()
        assert "proper names" in hint.lower()

    def test_faction_hints_preserve_ideology(self):
        hint = TOPIC_SCHEMA_HINTS["faction_research"]
        assert "ideology" in hint.lower()
        assert "origin story" in hint.lower()
        assert "proper names" in hint.lower()

    def test_lore_hints_preserve_causal_chains(self):
        hint = TOPIC_SCHEMA_HINTS["lore_research"]
        assert "causal chains" in hint.lower()
        assert "proper nouns" in hint.lower()


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
        topic0, header0, body0 = sections[0]
        topic1, header1, body1 = sections[1]
        assert topic0 == "zone_overview_research"
        assert header0 == "## ZONE OVERVIEW"
        assert "Zone info here." in body0
        assert "More zone info." in body0
        assert topic1 == "npc_research"
        assert header1 == "## NPCs AND NOTABLE CHARACTERS"
        assert "NPC info here." in body1

    def test_preserves_topic_order(self):
        blocks = [
            {"topic": "npc_research", "content": "NPCs first."},
            {"topic": "zone_overview_research", "content": "Zone second."},
        ]
        sections = _reconstruct_labeled_content(blocks)

        assert len(sections) == 2
        # NPC came first in input, should be first in output
        assert sections[0][1] == "## NPCs AND NOTABLE CHARACTERS"
        assert sections[1][1] == "## ZONE OVERVIEW"

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
        headers = [header for _, header, _ in sections]
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
        assert sections[0][1] == "## MYSTERY_TOPIC"


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


# --- Confidence caps ---


class TestApplyConfidenceCaps:
    def test_zero_npcs_caps_to_02(self):
        extraction = ZoneExtraction(zone=ZoneData(name="Test"))
        confidence = {"npcs": 0.9, "factions": 0.8}
        result = _apply_confidence_caps(extraction, confidence)
        assert result["npcs"] == 0.2

    def test_zero_factions_caps_to_02(self):
        extraction = ZoneExtraction(
            zone=ZoneData(name="Test"),
            npcs=[NPCData(name="NPC1", personality="brave", role="guard")],
        )
        confidence = {"npcs": 0.9, "factions": 0.8}
        result = _apply_confidence_caps(extraction, confidence)
        assert result["factions"] == 0.2
        assert result["npcs"] == 0.9  # NPCs not capped

    def test_majority_empty_personality_caps_to_04(self):
        extraction = ZoneExtraction(
            zone=ZoneData(name="Test"),
            npcs=[
                NPCData(name="NPC1", personality="", role="guard"),
                NPCData(name="NPC2", personality="", role="vendor"),
                NPCData(name="NPC3", personality="brave", role="boss"),
            ],
        )
        confidence = {"npcs": 0.85}
        result = _apply_confidence_caps(extraction, confidence)
        # 2/3 empty personality > 50%
        assert result["npcs"] == 0.4

    def test_majority_empty_role_caps_to_04(self):
        extraction = ZoneExtraction(
            zone=ZoneData(name="Test"),
            npcs=[
                NPCData(name="NPC1", personality="brave", role=""),
                NPCData(name="NPC2", personality="shy", role=""),
                NPCData(name="NPC3", personality="bold", role="guard"),
            ],
        )
        confidence = {"npcs": 0.85}
        result = _apply_confidence_caps(extraction, confidence)
        assert result["npcs"] == 0.4

    def test_normal_data_passes_through(self):
        extraction = ZoneExtraction(
            zone=ZoneData(name="Test"),
            npcs=[NPCData(name="NPC1", personality="brave", role="guard")],
            factions=[FactionData(name="Faction1")],
        )
        confidence = {"npcs": 0.9, "factions": 0.85, "zone": 0.95}
        result = _apply_confidence_caps(extraction, confidence)
        assert result["npcs"] == 0.9
        assert result["factions"] == 0.85
        assert result["zone"] == 0.95

    def test_already_low_confidence_not_raised(self):
        extraction = ZoneExtraction(zone=ZoneData(name="Test"))
        confidence = {"npcs": 0.1}
        result = _apply_confidence_caps(extraction, confidence)
        # 0.1 < 0.2 cap, so min(0.1, 0.2) = 0.1
        assert result["npcs"] == 0.1


# --- Quality warnings ---


class TestComputeQualityWarnings:
    def test_shallow_narrative_arc(self):
        extraction = ZoneExtraction(
            zone=ZoneData(name="Test", narrative_arc="Short arc."),
        )
        warnings = _compute_quality_warnings(extraction)
        assert "shallow_narrative_arc" in warnings

    def test_no_shallow_warning_for_long_arc(self):
        extraction = ZoneExtraction(
            zone=ZoneData(name="Test", narrative_arc="A" * 200),
        )
        warnings = _compute_quality_warnings(extraction)
        assert "shallow_narrative_arc" not in warnings

    def test_no_npc_personality_data(self):
        extraction = ZoneExtraction(
            zone=ZoneData(name="Test", narrative_arc="A" * 200),
            npcs=[
                NPCData(name="NPC1", personality=""),
                NPCData(name="NPC2", personality=""),
            ],
        )
        warnings = _compute_quality_warnings(extraction)
        assert "no_npc_personality_data" in warnings

    def test_no_personality_warning_when_some_have_data(self):
        extraction = ZoneExtraction(
            zone=ZoneData(name="Test", narrative_arc="A" * 200),
            npcs=[
                NPCData(name="NPC1", personality="brave"),
                NPCData(name="NPC2", personality=""),
            ],
        )
        warnings = _compute_quality_warnings(extraction)
        assert "no_npc_personality_data" not in warnings

    def test_no_personality_warning_when_no_npcs(self):
        extraction = ZoneExtraction(
            zone=ZoneData(name="Test", narrative_arc="A" * 200),
        )
        warnings = _compute_quality_warnings(extraction)
        assert "no_npc_personality_data" not in warnings

    def test_missing_antagonists_dungeon_zone(self):
        extraction = ZoneExtraction(
            zone=ZoneData(
                name="Test",
                narrative_arc="This zone has a dungeon called The Deadmines. " + "A" * 200,
            ),
            npcs=[NPCData(name="NPC1", role="quest_giver")],
            factions=[FactionData(name="Faction1")],
        )
        warnings = _compute_quality_warnings(extraction)
        assert "missing_antagonists" in warnings

    def test_no_missing_antagonists_when_boss_exists(self):
        extraction = ZoneExtraction(
            zone=ZoneData(
                name="Test",
                narrative_arc="This zone has a dungeon. " + "A" * 200,
            ),
            npcs=[NPCData(name="Boss1", role="boss")],
        )
        warnings = _compute_quality_warnings(extraction)
        assert "missing_antagonists" not in warnings

    def test_no_missing_antagonists_when_hostile_faction_exists(self):
        extraction = ZoneExtraction(
            zone=ZoneData(
                name="Test",
                narrative_arc="This zone has a dungeon. " + "A" * 200,
            ),
            factions=[FactionData(
                name="Defias Brotherhood",
                inter_faction=[FactionRelation(
                    faction_id="stormwind",
                    stance=FactionStance.HOSTILE,
                    description="Enemies of Stormwind",
                )],
            )],
        )
        warnings = _compute_quality_warnings(extraction)
        assert "missing_antagonists" not in warnings

    def test_no_missing_antagonists_no_dungeon_mention(self):
        extraction = ZoneExtraction(
            zone=ZoneData(
                name="Test",
                narrative_arc="A peaceful zone with farms and fields. " + "A" * 200,
            ),
        )
        warnings = _compute_quality_warnings(extraction)
        assert "missing_antagonists" not in warnings

    def test_lore_dungeon_mention_triggers_check(self):
        extraction = ZoneExtraction(
            zone=ZoneData(name="Test", narrative_arc="A" * 200),
            lore=[LoreData(
                title="The Deadmines",
                content="A dungeon beneath Moonbrook.",
            )],
            npcs=[NPCData(name="NPC1", role="quest_giver")],
        )
        warnings = _compute_quality_warnings(extraction)
        assert "missing_antagonists" in warnings


# --- Cross-reference with confidence caps ---


class TestCrossReferenceWithCaps:
    @pytest.mark.asyncio
    async def test_applies_confidence_caps(self):
        cp = _fresh_checkpoint()
        # Extraction with no factions — should cap factions confidence
        extraction = ZoneExtraction(
            zone=ZoneData(name="Elwynn Forest"),
            npcs=[NPCData(name="Marshal Dughan", personality="stern", role="guard")],
        )
        cp.step_data["extraction"] = extraction.model_dump(mode="json")
        researcher = _mock_researcher()
        # Mock returns high confidence for factions
        researcher.cross_reference = AsyncMock(return_value=CrossReferenceResult(
            is_consistent=True,
            confidence={"zone": 0.9, "npcs": 0.85, "factions": 0.8},
        ))

        await step_cross_reference(cp, researcher)

        cr = CrossReferenceResult.model_validate(cp.step_data["cross_reference"])
        # Factions should be capped to 0.2 (zero factions)
        assert cr.confidence["factions"] == 0.2
        # NPCs and zone should not be capped
        assert cr.confidence["npcs"] == 0.85
        assert cr.confidence["zone"] == 0.9


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

    @pytest.mark.asyncio
    async def test_includes_quality_warnings(self):
        """Package includes quality_warnings computed from extraction."""
        cp = _fresh_checkpoint()
        # Short narrative arc should trigger shallow_narrative_arc
        extraction = ZoneExtraction(
            zone=ZoneData(name="Test Zone", game="wow", narrative_arc="Short."),
            npcs=[NPCData(name="NPC1")],
            factions=[FactionData(name="Faction1")],
        )
        cr_result = CrossReferenceResult(
            is_consistent=True,
            confidence={"zone": 0.9},
        )
        cp.step_data["extraction"] = extraction.model_dump(mode="json")
        cp.step_data["cross_reference"] = cr_result.model_dump(mode="json")
        cp.step_data["research_sources"] = []
        researcher = _mock_researcher()

        await step_package_and_send(cp, researcher)

        pkg = cp.step_data["package"]
        assert "quality_warnings" in pkg
        assert "shallow_narrative_arc" in pkg["quality_warnings"]


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
        researcher.extract_category.assert_not_called()
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

