"""Tests for the LLM-powered research agent — orchestrator, dataclasses, prompts."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

import src.agent as agent_module
from src.agent import (
    EXTRACTION_CATEGORIES,
    OrchestratorContext,
    OrchestratorResult,
    ResearchContext,
)
from shared.prompt_loader import load_prompt
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
    ZoneExtraction,
    Conflict,
)
from tests.factories import (
    make_cross_ref,
    make_extraction,
    make_faction,
    make_item,
    make_lore,
    make_npc,
    make_source,
    make_zone,
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

    def test_loads_orchestrator_system_prompt(self):
        prompt = load_prompt(agent_module.__file__, "orchestrator_system")
        assert isinstance(prompt, str)
        assert "research_topic" in prompt
        assert "extract_category" in prompt
        assert "cross_reference" in prompt
        assert "discover_zones" in prompt

    def test_loads_orchestrator_task_prompt(self):
        prompt = load_prompt(agent_module.__file__, "orchestrator_task")
        assert isinstance(prompt, str)
        assert "{zone_name}" in prompt
        assert "{game_name}" in prompt
        assert "{skip_discovery}" in prompt


# --- Output models ---


class TestZoneExtraction:
    def test_minimal_extraction(self):
        extraction = make_extraction(zone=make_zone(name="Elwynn Forest"))
        assert extraction.zone.name == "Elwynn Forest"
        assert extraction.npcs == []
        assert extraction.factions == []

    def test_full_extraction(self):
        extraction = ZoneExtraction(
            zone=make_zone(name="Elwynn Forest"),
            npcs=[make_npc(name="Marshal Dughan")],
            factions=[make_faction(name="Stormwind Guard")],
            lore=[make_lore(title="History of Elwynn")],
            narrative_items=[make_item(name="Hogger's Claw")],
        )
        assert len(extraction.npcs) == 1
        assert len(extraction.factions) == 1
        assert len(extraction.lore) == 1
        assert len(extraction.narrative_items) == 1

    def test_serialization_roundtrip(self):
        extraction = ZoneExtraction(
            zone=make_zone(name="Westfall"),
            npcs=[make_npc(name="Gryan Stoutmantle")],
        )
        json_str = extraction.model_dump_json()
        restored = ZoneExtraction.model_validate_json(json_str)
        assert restored.zone.name == "Westfall"
        assert restored.npcs[0].name == "Gryan Stoutmantle"


class TestExtractionResultModels:
    """Tests for per-category extraction result wrapper models."""

    def test_npc_extraction_result_rejects_empty(self):
        with pytest.raises(ValidationError):
            NPCExtractionResult()

    def test_npc_extraction_result_rejects_empty_list(self):
        with pytest.raises(ValidationError):
            NPCExtractionResult(npcs=[])

    def test_npc_extraction_result_populated(self):
        result = NPCExtractionResult(npcs=[make_npc(name="Edwin VanCleef")])
        assert len(result.npcs) == 1
        assert result.npcs[0].name == "Edwin VanCleef"

    def test_faction_extraction_result_rejects_empty(self):
        with pytest.raises(ValidationError):
            FactionExtractionResult()

    def test_faction_extraction_result_rejects_empty_list(self):
        with pytest.raises(ValidationError):
            FactionExtractionResult(factions=[])

    def test_faction_extraction_result_populated(self):
        result = FactionExtractionResult(factions=[make_faction(name="Defias Brotherhood")])
        assert len(result.factions) == 1

    def test_lore_extraction_result_rejects_empty(self):
        with pytest.raises(ValidationError):
            LoreExtractionResult()

    def test_lore_extraction_result_rejects_empty_list(self):
        with pytest.raises(ValidationError):
            LoreExtractionResult(lore=[])

    def test_lore_extraction_result_populated(self):
        result = LoreExtractionResult(lore=[make_lore(title="Stonemasons' Betrayal")])
        assert len(result.lore) == 1

    def test_narrative_item_extraction_result_rejects_empty(self):
        with pytest.raises(ValidationError):
            NarrativeItemExtractionResult()

    def test_narrative_item_extraction_result_rejects_empty_list(self):
        with pytest.raises(ValidationError):
            NarrativeItemExtractionResult(narrative_items=[])

    def test_narrative_item_extraction_result_populated(self):
        result = NarrativeItemExtractionResult(
            narrative_items=[make_item(name="VanCleef's Sword")]
        )
        assert len(result.narrative_items) == 1

    def test_serialization_roundtrip(self):
        result = NPCExtractionResult(npcs=[make_npc(name="Test NPC", personality="Brave")])
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
            confidence={"zone": 0.5, "npcs": 0.4},
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
        assert ctx.crawl_cache == {}

    def test_accumulates(self):
        ctx = ResearchContext()
        ctx.raw_content.append("content 1")
        ctx.sources.append(SourceReference(url="https://x.com", domain="x.com", tier=SourceTier.PRIMARY))
        assert len(ctx.raw_content) == 1
        assert len(ctx.sources) == 1

    def test_shared_crawl_cache(self):
        shared_cache = {"https://wiki.gg/page": "cached content"}
        ctx = ResearchContext(crawl_cache=shared_cache)
        ctx.crawl_cache["https://wiki.gg/other"] = "new content"
        assert len(shared_cache) == 2


# --- OrchestratorContext ---


class TestOrchestratorContext:
    def test_defaults_empty_accumulators(self):
        ctx = OrchestratorContext(
            research_agent=MagicMock(),
            extraction_agents={},
            cross_ref_agent=MagicMock(),
            discovery_agent=MagicMock(),
            agent_file=__file__,
            zone_name="test_zone",
            game_name="wow",
            crawl_cache={},
        )
        assert ctx.research_content == {}
        assert ctx.sources == []
        assert ctx.zone_data is None
        assert ctx.npcs == []
        assert ctx.factions == []
        assert ctx.lore == []
        assert ctx.narrative_items == []
        assert ctx.cross_ref_result is None
        assert ctx.discovered_zones == []
        assert ctx.worker_tokens == 0

    def test_stores_worker_references(self):
        research = MagicMock()
        extraction = {"zone": MagicMock()}
        cross_ref = MagicMock()
        discovery = MagicMock()

        ctx = OrchestratorContext(
            research_agent=research,
            extraction_agents=extraction,
            cross_ref_agent=cross_ref,
            discovery_agent=discovery,
            agent_file=__file__,
            zone_name="elwynn_forest",
            game_name="wow",
            crawl_cache={},
        )

        assert ctx.research_agent is research
        assert ctx.extraction_agents is extraction
        assert ctx.cross_ref_agent is cross_ref
        assert ctx.discovery_agent is discovery


# --- OrchestratorResult ---


class TestOrchestratorResult:
    def test_empty_result(self):
        result = OrchestratorResult()
        assert result.zone_data is None
        assert result.npcs == []
        assert result.factions == []
        assert result.lore == []
        assert result.narrative_items == []
        assert result.sources == []
        assert result.cross_ref_result is None
        assert result.discovered_zones == []
        assert result.orchestrator_tokens == 0
        assert result.worker_tokens == 0

    def test_populated_result(self):
        result = OrchestratorResult(
            zone_data=make_zone(name="Elwynn Forest"),
            npcs=[make_npc(name="Marshal Dughan")],
            sources=[make_source()],
            orchestrator_tokens=1000,
            worker_tokens=5000,
        )
        assert result.zone_data.name == "Elwynn Forest"
        assert len(result.npcs) == 1
        assert result.orchestrator_tokens == 1000
        assert result.worker_tokens == 5000


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

    def test_creates_orchestrator(self):
        researcher = _make_researcher()
        assert researcher._orchestrator is not None

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


# --- research_zone (new orchestrator-based) ---


class TestResearchZone:
    @pytest.mark.asyncio
    async def test_returns_orchestrator_result(self):
        researcher = _make_researcher()

        mock_result = MagicMock()
        mock_result.output = "Research complete."
        usage = MagicMock()
        usage.total_tokens = 1500
        mock_result.usage.return_value = usage

        researcher._orchestrator = MagicMock()
        researcher._orchestrator.run = AsyncMock(return_value=mock_result)

        result = await researcher.research_zone("elwynn_forest")

        assert isinstance(result, OrchestratorResult)
        assert result.orchestrator_tokens == 1500
        researcher._orchestrator.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_context_with_workers(self):
        researcher = _make_researcher()

        mock_result = MagicMock()
        mock_result.output = "done"
        usage = MagicMock()
        usage.total_tokens = 100
        mock_result.usage.return_value = usage

        researcher._orchestrator = MagicMock()
        researcher._orchestrator.run = AsyncMock(return_value=mock_result)

        await researcher.research_zone("elwynn_forest")

        # Verify deps passed to orchestrator contain worker references
        call_kwargs = researcher._orchestrator.run.call_args[1]
        ctx = call_kwargs["deps"]
        assert isinstance(ctx, OrchestratorContext)
        assert ctx.zone_name == "elwynn_forest"
        assert ctx.game_name == "wow"
        assert ctx.research_agent is researcher._research_agent

    @pytest.mark.asyncio
    async def test_skip_discovery_in_prompt(self):
        researcher = _make_researcher()

        mock_result = MagicMock()
        mock_result.output = "done"
        usage = MagicMock()
        usage.total_tokens = 100
        mock_result.usage.return_value = usage

        researcher._orchestrator = MagicMock()
        researcher._orchestrator.run = AsyncMock(return_value=mock_result)

        await researcher.research_zone("elwynn_forest", skip_discovery=True)

        call_args = researcher._orchestrator.run.call_args[0]
        prompt = call_args[0]
        assert "Do NOT call discover_zones" in prompt

    @pytest.mark.asyncio
    async def test_no_skip_discovery_by_default(self):
        researcher = _make_researcher()

        mock_result = MagicMock()
        mock_result.output = "done"
        usage = MagicMock()
        usage.total_tokens = 100
        mock_result.usage.return_value = usage

        researcher._orchestrator = MagicMock()
        researcher._orchestrator.run = AsyncMock(return_value=mock_result)

        await researcher.research_zone("elwynn_forest")

        call_args = researcher._orchestrator.run.call_args[0]
        prompt = call_args[0]
        assert "Do NOT call discover_zones" not in prompt

    @pytest.mark.asyncio
    async def test_accumulates_zone_tokens(self):
        researcher = _make_researcher()

        mock_result = MagicMock()
        mock_result.output = "done"
        usage = MagicMock()
        usage.total_tokens = 2000
        mock_result.usage.return_value = usage

        # Simulate worker tokens accumulated during run
        async def mock_run(prompt, deps=None, **kwargs):
            deps.worker_tokens = 3000
            return mock_result

        researcher._orchestrator = MagicMock()
        researcher._orchestrator.run = AsyncMock(side_effect=mock_run)

        await researcher.research_zone("elwynn_forest")

        # zone_tokens = orchestrator (2000) + worker (3000)
        assert researcher.zone_tokens == 5000

    @pytest.mark.asyncio
    async def test_assembles_result_from_context(self):
        researcher = _make_researcher()

        zone_data = make_zone(name="Elwynn Forest")
        npcs = [make_npc(name="Dughan")]
        sources = [make_source()]
        cr_result = make_cross_ref()
        discovered = ["westfall"]

        async def mock_run(prompt, deps=None, **kwargs):
            deps.zone_data = zone_data
            deps.npcs = npcs
            deps.sources = sources
            deps.cross_ref_result = cr_result
            deps.discovered_zones = discovered
            deps.worker_tokens = 1000
            result = MagicMock()
            result.output = "done"
            usage = MagicMock()
            usage.total_tokens = 500
            result.usage.return_value = usage
            return result

        researcher._orchestrator = MagicMock()
        researcher._orchestrator.run = AsyncMock(side_effect=mock_run)

        result = await researcher.research_zone("elwynn_forest")

        assert result.zone_data is zone_data
        assert result.npcs is npcs
        assert result.sources is sources
        assert result.cross_ref_result is cr_result
        assert result.discovered_zones == ["westfall"]
        assert result.orchestrator_tokens == 500
        assert result.worker_tokens == 1000
